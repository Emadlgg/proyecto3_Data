"""Temporalidad y pronóstico académico; la publicación oficial se mantiene separada."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado
from src.ui.graficas import aplicar_tema
from src.ui.paleta import PRIMARIO, ESTIMACION, ACENTO, NEUTRO, NEUTRO_CLARO
from src.ui.analitica import cargar, datos_disponibles, version_aprobada, ultimo_candidato
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
st.subheader('2. Imputación obligatoria: enero–febrero 2026 (sin cobertura de telefonía)')
st.warning('Estimación, no observación. Los meses de enero y febrero de 2026 no tienen telefonía; '
           'las cifras se rotulan "Estimación" y no se presentan como dato oficial.')
imp = cargar('predicciones/imputacion_ene_feb_2026.csv')
bt_res = cargar('predicciones/backtest_imputacion_resumen.csv')
bt_det = cargar('predicciones/backtest_imputacion_detalle.csv')
perf_nac = cargar('predicciones/validacion_perfil_nacional_ene_feb_2026.csv')
hay_imp = datos_disponibles(imp, ['fecha', 'subdestino', 'segmento', 'metodo', 'visitantes_estimados', 'principal'])
obs = mensual.loc[mensual.subdestino.eq(sub) & mensual.segmento.eq(seg)].sort_values('fecha')
# Calendario completo: los meses sin cobertura quedan como hueco (nunca como cero ni interpolados).
if not obs.empty:
    cal = pd.date_range(obs.fecha.min(), obs.fecha.max(), freq='MS')
    obs = obs.set_index('fecha').reindex(cal).rename_axis('fecha').reset_index()
fig = go.Figure()
fig.add_trace(go.Scatter(x=obs.fecha, y=obs.visitantes, mode='lines+markers', name='Observado',
                         line=dict(color=PRIMARIO, width=2.5), connectgaps=False))
fig.add_vrect(x0='2025-12-16', x1='2026-02-15', fillcolor=ESTIMACION, opacity=.08, line_width=0,
              annotation_text='Sin cobertura telefónica', annotation_position='bottom left')
if hay_imp:
    g = imp.loc[imp.subdestino.eq(sub) & imp.segmento.eq(seg)]
    alt = g.loc[g.metodo.eq('interpolado_perfil')].sort_values('fecha')
    prin = g.loc[g.principal].sort_values('fecha')
    if not alt.empty:
        fig.add_trace(go.Scatter(x=alt.fecha, y=alt.visitantes_estimados, mode='lines+markers',
                                 name='Estimación alternativa (perfil estacional)',
                                 line=dict(dash='dot', color=ESTIMACION, width=1.5), opacity=.55,
                                 marker=dict(symbol='circle-open', size=9, color=ESTIMACION)))
    if not prin.empty:
        fig.add_trace(go.Scatter(x=prin.fecha, y=prin.visitantes_estimados, mode='lines+markers',
                                 name='Estimación (principal)',
                                 line=dict(dash='dash', color=ESTIMACION, width=2.5),
                                 marker=dict(symbol='diamond', size=11, color=ESTIMACION)))
else:
    st.info('Genera la imputación con python -m src.imputacion.')
fig.update_layout(xaxis_title='Mes', yaxis_title='Visitantes del polígono')
st.plotly_chart(aplicar_tema(fig, 'Observado (azul) vs Estimación (terracota, punteada)'), width='stretch')
st.caption('Método principal: factor de reparto (visitantes ÷ migración nacional) interpolado entre dic-2025 y '
           'mar-2026, multiplicado por la migración nacional de Base_Migracion. La línea tenue usa el perfil '
           'estacional de migración en lugar de la migración observada. No sumar polígonos.')

if datos_disponibles(bt_res, ['metodo', 'MAE', 'RMSE', 'MAPE', 'n']):
    st.markdown('**Validación del método (ocultando 2 meses con vecinos observados)**')
    fila = bt_res.loc[bt_res.metodo.eq('interpolado_observada')]
    if not fila.empty:
        f0 = fila.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric('MAPE', f"{f0.MAPE:.1f}%", help='Error porcentual absoluto medio, todos los grupos.')
        c2.metric('MAE', f"{f0.MAE:,.0f}", help='Error absoluto medio en visitantes.')
        c3.metric('RMSE', f"{f0.RMSE:,.0f}", help='Raíz del error cuadrático medio, en visitantes.')
    mg = bt_det.loc[bt_det.metodo.eq('interpolado_observada') & bt_det.subdestino.eq(sub)
                    & bt_det.segmento.eq(seg)] if datos_disponibles(bt_det, ['metodo', 'subdestino', 'segmento']) else pd.DataFrame()
    if not mg.empty:
        st.caption(f"Para este grupo: MAPE {mg.error_pct_abs.mean():.1f}% · MAE {mg.error.abs().mean():,.0f} "
                   f"sobre {len(mg)} meses ocultados.")
    with st.expander('Comparación de métodos en la validación'):
        tabla = bt_res[['etiqueta', 'tipo', 'MAE', 'RMSE', 'MAPE', 'n']].rename(
            columns={'etiqueta': 'Método', 'tipo': 'Tipo', 'n': 'Observaciones'})
        st.dataframe(tabla.round(1), hide_index=True, width='stretch')
        st.caption('Muestra pequeña (2 ventanas × 6 grupos × 2 meses): interpretar como evidencia indicativa. '
                   'Las "referencias" no usan migración y sirven solo de comparación.')
if datos_disponibles(perf_nac, ['fecha', 'migracion_nacional_estimada', 'viajeros_nacionales', 'error_pct']):
    with st.expander('¿Por qué no se usa solo el perfil estacional?'):
        t = perf_nac.assign(mes=perf_nac.fecha.dt.strftime('%Y-%m'))[
            ['mes', 'migracion_nacional_estimada', 'viajeros_nacionales', 'error_pct']].rename(columns={
                'mes': 'Mes', 'migracion_nacional_estimada': 'Perfil estacional (estimado)',
                'viajeros_nacionales': 'Migración observada', 'error_pct': 'Error (%)'})
        st.dataframe(t.round(1), hide_index=True, width='stretch')
        st.caption('El perfil 2017–2024 sobrestimó la migración nacional de ene–feb 2026; por eso el método '
                   'principal usa la migración observada y deja el perfil como alternativa.')

st.subheader('Estado de publicación oficial (MLOps)')
version = version_aprobada()
if version is None:
    cand = ultimo_candidato()
    if cand is None:
        st.info('No hay versión oficial aprobada ni ejecuciones del pipeline en este entorno. '
                'Las estimaciones de arriba son exploratorias, para análisis académico.')
    elif cand['aprobado'] is None:
        st.error(f"La última ejecución del pipeline ({cand['run_id']}) falló y no produjo una decisión: "
                 f"{'; '.join(cand['errores']) or 'sin detalle'}. No hay versión oficial.")
    elif cand['aprobado']:
        st.info(f"Último candidato ({cand['run_id']}) cumple los umbrales, pero no está publicado. "
                'Las estimaciones de arriba son exploratorias.')
    else:
        st.warning(f"Sin versión oficial: el último candidato evaluado ({cand['run_id']}) fue rechazado. "
                   'Las estimaciones de arriba son exploratorias, para análisis académico.')
        c1, c2, c3 = st.columns(3)
        c1.metric('MAE del candidato', f"{cand['mae_modelo']:,.0f}",
                  help='Error absoluto medio del candidato en la evaluación rolling origin oct–dic 2025.')
        c2.metric('MAE de la referencia', f"{cand['mae_referencia']:,.0f}",
                  help='Referencia: último valor mensual observado.')
        c3.metric('Razón MAE (candidato ÷ referencia)', f"{cand['ratio_mae']:.2f}",
                  help=f"Se aprueba solo si es ≤ {cand['umbral_ratio']:.2f}.")
        st.caption(f"Decisión del pipeline: {cand['razon']}. Los umbrales se fijaron antes de ejecutar y no se modifican tras ver resultados.")
    st.caption('Nota: el pipeline MLOps evalúa el método anterior (factor mediano × perfil estacional). '
               'Las estimaciones de este módulo provienen de la imputación (src.imputacion), que se valida '
               'con su propio backtest de meses ocultos.')
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

