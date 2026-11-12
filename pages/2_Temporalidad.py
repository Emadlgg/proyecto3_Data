"""Temporalidad y pronóstico académico; la publicación oficial se mantiene separada."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado
from src.ui.graficas import aplicar_tema
from src.ui.paleta import PRIMARIO, ESTIMACION, ACENTO, NEUTRO, NEUTRO_CLARO
from src.ui.analitica import cargar, datos_disponibles, version_aprobada
from src.visualizaciones_extra import (serie_diaria, lift_eventos, lift_por_evento,
                                       fin_de_semana_vs_habiles)

st.set_page_config(page_title='Temporalidad | Petén', layout='wide')
aplicar_estilos()
encabezado('Temporalidad y predicciones', 'Patrones diarios, festividades y estimaciones con evaluación.', 'Telefonía y pronósticos exploratorios')

DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


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

st.subheader('1. Presencias diarias y efecto de festividades')
st.caption('No sumar presencias diarias para inferir visitantes únicos mensuales. '
           'Selecciona un punto de la serie para ver el detalle de ese día y resaltarlo en el patrón semanal.')
if d.empty:
    st.info('Selecciona al menos un evento con registros.')
else:
    daily = (d.groupby(['fecha', 'evento'], as_index=False).presencias_diarias.sum()
             .sort_values('fecha'))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily.fecha, y=daily.presencias_diarias, mode='lines',
                             line=dict(color=NEUTRO_CLARO, width=1.5), hoverinfo='skip',
                             showlegend=False))
    for ev, g in daily.groupby('evento'):
        regular = str(ev).strip().casefold() == 'regular'
        fig.add_trace(go.Scatter(x=g.fecha, y=g.presencias_diarias, mode='markers', name=str(ev),
                                 marker=dict(size=6 if regular else 9,
                                             color=NEUTRO if regular else None,
                                             opacity=.55 if regular else 1)))
    fig.update_layout(xaxis_title='Fecha', yaxis_title='Presencias diarias', hovermode='closest')
    evento_sel = st.plotly_chart(aplicar_tema(fig, 'Presencias diarias por tipo de día (huecos = sin dato)'),
                                 width='stretch', on_select='rerun', selection_mode='points',
                                 key='temp_diaria')
    puntos = getattr(getattr(evento_sel, 'selection', None), 'points', []) or []
    fecha_sel = None
    if puntos:
        try:
            fecha_sel = pd.Timestamp(puntos[0]['x']).normalize()
        except (ValueError, TypeError, KeyError):
            fecha_sel = None

    if fecha_sel is not None:
        fila = daily.loc[daily.fecha.dt.normalize().eq(fecha_sel)]
        if not fila.empty:
            f0 = fila.iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric('Día seleccionado', f"{fecha_sel:%Y-%m-%d} ({DIAS[fecha_sel.dayofweek]})")
            c2.metric('Evento', str(f0.evento))
            c3.metric('Presencias', f'{f0.presencias_diarias:,.0f}')

    left, right = st.columns(2)
    with left:
        st.markdown('**Patrón semanal**')
        sem = daily.assign(dow=daily.fecha.dt.dayofweek).groupby('dow', as_index=False).presencias_diarias.mean()
        sem['nombre'] = sem.dow.map(dict(enumerate(DIAS)))
        sem['color'] = [ACENTO if (fecha_sel is not None and r == fecha_sel.dayofweek) else PRIMARIO
                        for r in sem.dow]
        figs = go.Figure(go.Bar(x=sem.nombre, y=sem.presencias_diarias, marker_color=sem.color))
        figs.update_layout(xaxis_title='Día', yaxis_title='Media diaria de presencias')
        st.plotly_chart(aplicar_tema(figs, 'Media por día de la semana'), width='stretch')
        fs = fin_de_semana_vs_habiles(serie_diaria(d, sub))
        if pd.notna(fs['diferencia_pct']):
            st.metric('Fin de semana vs días hábiles', f"{fs['diferencia_pct']:+.1f}%",
                      help='Media diaria sáb–dom frente a media diaria lun–vie en la selección.')
    with right:
        st.markdown('**Lift por festividad**')
        lf = lift_por_evento(d)
        if lf.empty:
            st.info('No hay días regulares comparables suficientes para calcular lift. '
                    'Incluye "Regular" en los eventos visibles.')
        else:
            figl = go.Figure(go.Bar(
                x=lf.lift_medio_pct, y=lf.evento, orientation='h',
                marker_color=[PRIMARIO if v >= 0 else ESTIMACION for v in lf.lift_medio_pct],
                customdata=lf[['dias']].values,
                hovertemplate='%{y}: %{x:+.1f}% (n=%{customdata[0]} días)<extra></extra>'))
            figl.add_vline(x=0, line_dash='dash', line_color=NEUTRO)
            figl.update_layout(xaxis_title='Lift vs día regular (%)', yaxis=dict(autorange='reversed'),
                               hovermode='closest')
            st.plotly_chart(aplicar_tema(figl, 'Impacto medio por festividad'), width='stretch')
            st.caption('Lift = presencia del día festivo / media de días regulares del mismo día de semana − 1. '
                       'Festividades con pocos días (n bajo) son indicativas, no concluyentes.')
        with st.expander('Ver lift por fecha'):
            ld = lift_eventos(d)
            ld = ld.loc[ld.lift_pct.notna(), ['fecha', 'evento', 'presencias_diarias', 'referencia', 'lift_pct']]
            st.dataframe(ld.sort_values('fecha'), hide_index=True, width='stretch')

st.divider()
st.subheader('2. Pronóstico académico obligatorio: enero–febrero 2026')
st.warning('Estimación exploratoria, NO APROBADA para publicación oficial. '
           'El método de reparto estacional no superó la referencia en la evaluación MLOps '
           '(control de calidad previo a publicar cifras oficiales).')
pred = cargar('predicciones/prediccion_peten_ene_feb_2026.csv')
metricas = cargar('predicciones/metricas_prediccion.csv')
obs = mensual.loc[mensual.subdestino.eq(sub) & mensual.segmento.eq(seg)].sort_values('fecha')
# Calendario completo: los meses sin cobertura quedan como hueco (nunca como cero ni interpolados).
if not obs.empty:
    cal = pd.date_range(obs.fecha.min(), obs.fecha.max(), freq='MS')
    obs = obs.set_index('fecha').reindex(cal).rename_axis('fecha').reset_index()
fig = go.Figure()
fig.add_trace(go.Scatter(x=obs.fecha, y=obs.visitantes, mode='lines+markers', name='Observado',
                         line=dict(color=PRIMARIO, width=2.5), connectgaps=False))
fig.add_vrect(x0='2025-12-16', x1='2026-02-15', fillcolor=ESTIMACION, opacity=.08, line_width=0,
              annotation_text='Sin cobertura telefónica', annotation_position='top left')
if datos_disponibles(pred, ['fecha','subdestino','segmento','visitantes_estimados']):
    p = pred.loc[pred.subdestino.eq(sub) & pred.segmento.eq(seg)].sort_values('fecha')
    p = p.loc[p.fecha.dt.year.eq(2026) & p.fecha.dt.month.isin([1,2])]
    if not p.empty:
        fig.add_trace(go.Scatter(x=p.fecha, y=p.visitantes_estimados, mode='lines+markers',
                                 name='Estimación (no aprobada)',
                                 line=dict(dash='dash', color=ESTIMACION, width=2.5),
                                 marker=dict(symbol='diamond', size=11, color=ESTIMACION)))
    else:
        st.info('Sin estimaciones exploratorias para el grupo seleccionado.')
else:
    st.info('Genera las estimaciones con python -m src.predicciones.')
fig.update_layout(xaxis_title='Mes', yaxis_title='Visitantes del polígono')
st.plotly_chart(aplicar_tema(fig, 'Observado (azul) vs Estimación (terracota, punteada)'), width='stretch')
if datos_disponibles(metricas, ['subdestino','segmento','MAE','RMSE']):
    m = metricas.loc[metricas.subdestino.eq(sub) & metricas.segmento.eq(seg)]
    if not m.empty:
        cols = st.columns(3)
        cols[0].metric('MAE retrospectivo', f'{float(m.MAE.iloc[0]):,.0f}')
        cols[1].metric('RMSE retrospectivo', f'{float(m.RMSE.iloc[0]):,.0f}')
        if 'MAPE' in m.columns and pd.notna(m.MAPE.iloc[0]):
            cols[2].metric('MAPE retrospectivo', f'{float(m.MAPE.iloc[0]):.1f}%')
        st.caption('Validación leave-one-month-out sobre sep–dic 2025 (4 meses por grupo); '
                   'no equivale a evaluación prospectiva de enero–febrero 2026.')
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
