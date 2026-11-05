"""Temporalidad y pronóstico académico; la publicación oficial se mantiene separada."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado
from src.ui.graficas import aplicar_tema
from src.ui.analitica import cargar, datos_disponibles, version_aprobada
from src.visualizaciones_extra import serie_diaria, patron_semanal, lift_eventos

st.set_page_config(page_title='Temporalidad | Petén', layout='wide')
aplicar_estilos()
encabezado('Temporalidad y predicciones', 'Patrones diarios, festividades y estimaciones con evaluación.', 'Telefonía y pronósticos exploratorios')

@st.cache_data(show_spinner=False)
def datos():
    return cargar('movilidad_diaria_peten.csv'), cargar('movilidad_mensual_peten.csv')

diaria, mensual = datos()
if not datos_disponibles(diaria, ['fecha','subdestino','evento','presencias_diarias']) or not datos_disponibles(mensual, ['fecha','subdestino','segmento','visitantes']):
    st.error('Faltan datos procesados de movilidad. Ejecuta el ETL.'); st.stop()
subs = sorted(diaria.subdestino.dropna().unique().tolist())
if not subs:
    st.info('No hay subdestinos.'); st.stop()
sub = st.sidebar.selectbox('Subdestino', subs)
segmentos = sorted(mensual.loc[mensual.subdestino.eq(sub), 'segmento'].dropna().unique().tolist())
if not segmentos:
    st.info('No hay segmentos.'); st.stop()
seg = st.sidebar.selectbox('Segmento', segmentos)
original = diaria.loc[diaria.subdestino.eq(sub)].copy()
eventos = sorted(original.evento.dropna().unique().tolist())
seleccion = st.sidebar.multiselect('Eventos visibles', eventos, default=eventos)
d = original.loc[original.evento.isin(seleccion)]
st.subheader('Presencias diarias')
st.caption('No sumar presencias diarias para inferir visitantes únicos mensuales.')
if d.empty:
    st.info('Selecciona al menos un evento con registros.')
else:
    daily = serie_diaria(d, sub)
    fig = px.scatter(daily, x='fecha', y='presencias_diarias', labels={'fecha':'Fecha','presencias_diarias':'Presencias'})
    st.plotly_chart(aplicar_tema(fig, 'Fechas observadas'), width='stretch')
    semanal = patron_semanal(daily)
    fig = px.bar(semanal, x='nombre', y='presencias_diarias', labels={'nombre':'Día','presencias_diarias':'Media diaria'})
    st.plotly_chart(aplicar_tema(fig, 'Patrón semanal'), width='stretch')
    lifts = lift_eventos(d)
    lifts = lifts.loc[lifts.lift_pct.notna()]
    if lifts.empty:
        st.info('No hay días regulares comparables suficientes para calcular lift.')
    else:
        fig = px.bar(lifts, x='fecha', y='lift_pct', color='evento', labels={'fecha':'Fecha','lift_pct':'Lift (%)'})
        fig.add_hline(y=0, line_dash='dash')
        st.plotly_chart(aplicar_tema(fig, 'Impacto de eventos frente a días comparables'), width='stretch')

st.divider()
st.subheader('Pronóstico académico obligatorio: enero–febrero 2026')
st.warning('Estimación exploratoria, NO APROBADA para publicación oficial. El método de reparto estacional no superó la referencia en la evaluación MLOps.')
pred = cargar('predicciones/prediccion_peten_ene_feb_2026.csv')
metricas = cargar('predicciones/metricas_prediccion.csv')
obs = mensual.loc[mensual.subdestino.eq(sub) & mensual.segmento.eq(seg)].sort_values('fecha')
fig = go.Figure()
fig.add_trace(go.Scatter(x=obs.fecha, y=obs.visitantes, mode='lines+markers', name='Observado'))
if datos_disponibles(pred, ['fecha','subdestino','segmento','visitantes_estimados']):
    p = pred.loc[pred.subdestino.eq(sub) & pred.segmento.eq(seg)].sort_values('fecha')
    p = p.loc[p.fecha.dt.year.eq(2026) & p.fecha.dt.month.isin([1,2])]
    if not p.empty:
        fig.add_trace(go.Scatter(x=p.fecha, y=p.visitantes_estimados, mode='lines+markers', line=dict(dash='dash'), marker=dict(symbol='diamond',size=11), name='Estimación exploratoria (no aprobada)'))
    else:
        st.info('Sin estimaciones exploratorias para el grupo seleccionado.')
else:
    st.info('Genera las estimaciones con python -m src.predicciones.')
st.plotly_chart(aplicar_tema(fig, 'Observado y estimado (categorías diferenciadas)'), width='stretch')
if datos_disponibles(metricas, ['subdestino','segmento','MAE','RMSE']):
    m = metricas.loc[metricas.subdestino.eq(sub) & metricas.segmento.eq(seg)]
    if not m.empty:
        a, b = st.columns(2)
        a.metric('MAE retrospectivo del grupo', f'{float(m.MAE.iloc[0]):,.2f}')
        b.metric('RMSE retrospectivo del grupo', f'{float(m.RMSE.iloc[0]):,.2f}')
        st.caption('Validación leave-one-month-out sobre sep–dic 2025; no equivale a evaluación prospectiva de enero–febrero 2026.')
else:
    st.info('Métricas por grupo no disponibles. Ejecuta python -m src.predicciones.')

st.subheader('Estado de publicación oficial (MLOps)')
version = version_aprobada()
if version is None:
    st.info('No hay versión real aprobada. Las estimaciones anteriores se muestran solo para análisis académico.')
else:
    archivo, meta = version
    st.success(f"Versión aprobada disponible: {meta.get('run_id', 'sin identificador')}")
    with st.expander('Consultar predicciones oficialmente aprobadas'):
        try:
            aprobado = pd.read_csv(archivo, parse_dates=['fecha'])
            requeridas = {'fecha','subdestino','segmento','visitantes_estimados'}
            if not requeridas.issubset(aprobado.columns):
                st.error('La versión aprobada no tiene el esquema esperado.')
            else:
                st.dataframe(aprobado.loc[aprobado.subdestino.eq(sub) & aprobado.segmento.eq(seg)], hide_index=True, width='stretch')
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            st.error(f'No se pudo leer la versión aprobada: {exc}')
st.caption('Enero y febrero de 2026 no tienen observaciones telefónicas; ausencia de cobertura no equivale a cero. No sumar polígonos.')
