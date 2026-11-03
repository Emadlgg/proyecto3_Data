"""Módulo 2: dinámica temporal, eventos y pronóstico de Petén."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.visualizaciones_extra import leer, serie_diaria, patron_semanal, lift_eventos
from src.publicacion import consultar
from pathlib import Path

st.set_page_config(page_title='Temporalidad y pronósticos | Petén', layout='wide')
st.title('Dinámica temporal y pronósticos')
st.caption('Telefonía: presencias diarias y visitantes mensuales no son equivalentes. Las estimaciones de 2026 se identifican por separado.')

@st.cache_data
def cargar():
    return (leer('movilidad_diaria_peten.csv', carpeta=''),
            leer('movilidad_mensual_peten.csv', carpeta=''),
            )

try:
    diaria, mensual = cargar()
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc)); st.stop()

subs = sorted(set(diaria.subdestino.dropna()) & set(mensual.subdestino.dropna()))
if not subs:
    st.warning('No hay subdestinos coincidentes.'); st.stop()
sub = st.sidebar.selectbox('Subdestino', subs)
segmentos = sorted(mensual.loc[mensual.subdestino.eq(sub), 'segmento'].dropna().unique())
seg = st.sidebar.selectbox('Segmento para pronósticos', segmentos)
fechas = sorted(diaria.loc[diaria.subdestino.eq(sub),'fecha'].dropna().unique())
if not fechas:
    st.warning('Sin registros diarios.'); st.stop()
rango = st.sidebar.date_input('Período diario', value=(pd.Timestamp(fechas[0]).date(), pd.Timestamp(fechas[-1]).date()),
                                    min_value=pd.Timestamp(fechas[0]).date(), max_value=pd.Timestamp(fechas[-1]).date())
if not isinstance(rango, (tuple, list)) or len(rango) != 2:
    st.info('Selecciona fecha inicial y final.'); st.stop()
inicio, fin = rango
if inicio > fin:
    st.warning('El inicio debe ser anterior al final.'); st.stop()
base = diaria.loc[diaria.subdestino.eq(sub) & diaria.fecha.between(pd.Timestamp(inicio), pd.Timestamp(fin))].copy()
if base.empty:
    st.info('No hay datos en el período seleccionado.'); st.stop()

st.subheader('Presencia diaria')
st.info('La base diaria contiene ventanas de eventos y períodos discontinuos. Las líneas no implican cobertura continua entre fechas sin registros.')
eventos = sorted(base.evento.dropna().unique())
sel_eventos = st.multiselect('Eventos/categorías visibles', eventos, default=eventos)
d = base.loc[base.evento.isin(sel_eventos)]
if d.empty:
    st.info('Selecciona al menos una categoría con datos.')
else:
    d1 = serie_diaria(d, sub)
    fig = px.scatter(d1, x='fecha', y='presencias_diarias', title='Presencias por fecha observada',
                     labels={'presencias_diarias':'Presencias (no visitantes únicos)', 'fecha':'Fecha'})
    st.plotly_chart(fig, width='stretch')
    semanal = patron_semanal(d1)
    fig2 = px.bar(semanal, x='nombre', y='presencias_diarias', title='Presencia diaria media según día de semana',
                  labels={'nombre':'Día','presencias_diarias':'Media de presencias'})
    st.plotly_chart(fig2, width='stretch')

st.subheader('Eventos y diferencia respecto a días regulares')
st.caption('Comparación descriptiva dentro de la cobertura disponible. No demuestra causalidad ni controla por temporada u otros factores.')
lev = lift_eventos(base)
lev = lev.loc[lev.lift_pct.notna()]
if lev.empty:
    st.info('No hay suficientes días regulares comparables para calcular un lift de eventos confiable.')
else:
    fig3 = px.bar(lev, x='fecha', y='lift_pct', color='evento', barmode='group',
                  title='Diferencia porcentual frente a días regulares del mismo día de semana',
                  labels={'lift_pct':'Diferencia (%)', 'fecha':'Fecha'})
    fig3.add_hline(y=0, line_dash='dash')
    st.plotly_chart(fig3, width='stretch')
    with st.expander('Detalle del cálculo de eventos'):
        st.dataframe(lev[['fecha','evento','presencias_diarias','referencia','lift_pct']], hide_index=True)

st.subheader('Estimaciones de enero y febrero de 2026 — publicación controlada')
# Nunca consultar data/processed/predicciones como si fuera una version aprobada.
try:
    aprobada = consultar(Path(__file__).resolve().parents[1] / 'artifacts')
except (ValueError, KeyError, FileNotFoundError, OSError) as exc:
    st.error(f'No es posible verificar la integridad de la version aprobada: {exc}')
    st.stop()
if aprobada is None:
    st.warning('No hay estimaciones aprobadas disponibles. El ultimo candidato real fue rechazado por la regla de aceptacion. Se conservan los datos observados.')
    obs = mensual.loc[mensual.subdestino.eq(sub) & mensual.segmento.eq(seg), ['fecha','visitantes']].sort_values('fecha')
    if not obs.empty:
        st.plotly_chart(px.line(obs, x='fecha', y='visitantes', markers=True,
                                title='Visitantes observados (sin pronosticos publicados)'), width='stretch')
else:
    ruta, meta = aprobada
    if meta.get('demo_sintetica'):
        st.error('La version activa es sintetica; no puede mostrarse como prediccion institucional.')
        st.stop()
    pron = pd.read_csv(ruta, parse_dates=['fecha'])
    obs = mensual.loc[mensual.subdestino.eq(sub) & mensual.segmento.eq(seg), ['fecha','visitantes']].sort_values('fecha')
    est = pron.loc[pron.subdestino.eq(sub) & pron.segmento.eq(seg)].sort_values('fecha')
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=obs.fecha, y=obs.visitantes, mode='lines+markers', name='Observado'))
    fig4.add_trace(go.Scatter(x=est.fecha, y=est.visitantes_estimados, mode='markers',
                              marker={'symbol':'diamond','size':12}, name='Estimacion aprobada'))
    fig4.update_layout(title=f'Visitantes del poligono — {sub} / {seg}', xaxis_title='Mes', yaxis_title='Visitantes')
    st.plotly_chart(fig4, width='stretch')
    st.caption(f"Version: {meta.get('run_id')} | Generada: {meta.get('generado_utc')} | "
               f"MAE validacion: {meta.get('metrica_validacion_mae')} | "
               f"Procedimiento: {meta.get('version_procedimiento')} | Unidad: {meta.get('unidad')}")
    st.info('Las estimaciones no son observaciones de telefonia ni visitantes unicos de todo Peten. Enero y febrero de 2026 no tienen cobertura telefonica comparable.')
