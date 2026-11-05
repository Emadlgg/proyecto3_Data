"""Demanda por poligono y mercados emisores, sin sumar poligonos solapados."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado, aviso_metodologico
from src.ui.graficas import aplicar_tema
from src.ui.analitica import cargar, datos_disponibles, detalle_mes
from src.mercados_emisores import top_mercados

st.set_page_config(page_title='Demanda | Peten', layout='wide')
aplicar_estilos()
encabezado('Demanda turistica', 'Evolucion, composicion, permanencia y mercados emisores por poligono.', 'Telefonia procesada; no equivale a visitantes unicos de Peten')

@st.cache_data(show_spinner=False)
def datos():
    return (cargar('indicadores/visitantes_subdestino.csv'),
            cargar('indicadores/estadia_ponderada.csv'),
            cargar('indicadores/segmentacion_visitantes.csv'),
            cargar('indicadores/mercados_emisores_peten.csv'))

v, e, s, mercados = datos()
if not all((datos_disponibles(v, ['fecha','subdestino','visitantes','dias_persona']),
            datos_disponibles(e, ['fecha','subdestino','visitantes','dias_persona']),
            datos_disponibles(s, ['fecha','subdestino','turistas_pernocta','excursionistas']))):
    st.error('Faltan indicadores. Ejecuta python -m src.indicadores.'); st.stop()
subs = sorted(v.subdestino.dropna().unique().tolist())
fechas = sorted(pd.Timestamp(x).normalize() for x in v.fecha.dropna().unique())
if not subs or not fechas:
    st.info('No hay observaciones disponibles.'); st.stop()
if st.session_state.get('dem_sub') not in subs:
    st.session_state['dem_sub'] = subs[0]
if pd.Timestamp(st.session_state.get('dem_mes', fechas[-1])) not in fechas:
    st.session_state['dem_mes'] = fechas[-1]
# Aplicar seleccion pendiente ANTES de instanciar el selector.
pendiente = st.session_state.pop('dem_mes_pendiente', None)
if pendiente is not None and pd.Timestamp(pendiente) in fechas:
    st.session_state['dem_mes'] = pd.Timestamp(pendiente)
st.sidebar.header('Filtros de demanda')
sub = st.sidebar.selectbox('Subdestino', subs, key='dem_sub')
mes = pd.Timestamp(st.sidebar.selectbox('Mes de detalle', fechas,
                       format_func=lambda x: pd.Timestamp(x).strftime('%Y-%m'), key='dem_mes'))
serie = v.loc[v.subdestino.eq(sub)].sort_values('fecha').copy()
serie[['visitantes','dias_persona']] = serie[['visitantes','dias_persona']].apply(pd.to_numeric, errors='coerce')
serie = serie.dropna(subset=['visitantes','dias_persona'])
pernocta = e.loc[e.subdestino.eq(sub)].copy()
pernocta[['visitantes','dias_persona']] = pernocta[['visitantes','dias_persona']].apply(pd.to_numeric, errors='coerce')
pernocta = pernocta.dropna(subset=['visitantes','dias_persona'])
base_pernocta = pernocta.visitantes.sum()
estadia = pernocta.dias_persona.sum() / base_pernocta if base_pernocta > 0 else float('nan')
mes_detalle = detalle_mes(v, mes, [sub])
a,b,c = st.columns(3)
a.metric('Visitantes promedio por mes (poligono)', f'{serie.visitantes.mean():,.0f}' if not serie.empty else 'Sin datos')
b.metric('Dias-persona (mes seleccionado)', f'{pd.to_numeric(mes_detalle.dias_persona, errors="coerce").sum():,.0f}' if not mes_detalle.empty else 'Sin datos')
c.metric('Estadia ponderada (solo pernocta)', f'{estadia:.2f} dias' if pd.notna(estadia) else 'No aplica')
st.caption('Promedio sobre meses observados. Estadia: suma de dias-persona / suma de visitantes con pernocta; no promedio de promedios.')

st.subheader('1. Evolucion mensual: selecciona una barra')
fig1 = px.bar(serie, x='fecha', y='visitantes', labels={'fecha':'Mes','visitantes':'Visitantes del poligono'})
fig1.update_traces(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=.35)))
evento = st.plotly_chart(aplicar_tema(fig1, 'Evolucion del subdestino'), width='stretch', on_select='rerun', selection_mode='points', key='dem_evolucion')
points = getattr(getattr(evento, 'selection', None), 'points', []) or []
if points:
    try:
        nuevo = pd.Timestamp(points[0]['x']).normalize()
        if nuevo in fechas and nuevo != mes:
            st.session_state['dem_mes_pendiente'] = nuevo
            st.rerun()
    except (ValueError, TypeError, KeyError):
        pass
st.caption('Seleccionar una barra actualiza la composicion y la estadia del mes.')
left,right = st.columns(2)
with left:
    st.subheader('2. Turistas y excursionistas')
    d = detalle_mes(s, mes, [sub])
    if d.empty:
        st.info('Sin datos para este mes.')
    else:
        vals = d[['turistas_pernocta','excursionistas']].apply(pd.to_numeric, errors='coerce').sum()
        if vals.sum() > 0:
            fig2 = px.pie(names=['Con pernocta','Sin pernocta'], values=vals.values, hole=.5)
            st.plotly_chart(aplicar_tema(fig2, 'Composicion del mes'), width='stretch')
        else:
            st.info('Sin valores positivos para composicion.')
with right:
    st.subheader('3. Estadia del mes')
    d = detalle_mes(e, mes, [sub])
    if d.empty:
        st.info('Sin datos de estadia.')
    else:
        num = pd.to_numeric(d.dias_persona, errors='coerce').sum()
        den = pd.to_numeric(d.visitantes, errors='coerce').sum()
        st.metric('Dias por visitante con pernocta', f'{num/den:.2f}' if den > 0 else 'No aplica')
        st.caption('Solo segmento mayor a 1 dia.')
st.subheader('Comparacion de poligonos (sin sumar)')
d = detalle_mes(v, mes, subs)
if not d.empty:
    fig3 = px.bar(d, x='subdestino', y='visitantes', labels={'subdestino':'Poligono','visitantes':'Visitantes'})
    st.plotly_chart(aplicar_tema(fig3, 'Poligonos individuales'), width='stretch')

st.divider()
st.subheader('4. Mercados emisores: Top 10 paises extranjeros')
if not datos_disponibles(mercados, ['fecha','subdestino','pais','mercado','visitantes']):
    st.info('Falta el indicador de mercados. Ejecuta python -m src.mercados_emisores.')
else:
    st.caption('Fuente: hoja Peten de BD_moviidad_mensual.xlsx. Ranking por poligono, sin sumar subdestinos.')
    meses_mercados = sorted(pd.Timestamp(x) for x in mercados.loc[mercados.subdestino.eq(sub),'fecha'].dropna().unique())
    periodos = st.multiselect('Meses para mercados emisores', meses_mercados, default=meses_mercados,
                             format_func=lambda x: pd.Timestamp(x).strftime('%Y-%m'))
    m = mercados.loc[mercados.subdestino.eq(sub) & mercados.fecha.isin(periodos)].copy()
    if m.empty:
        st.info('Selecciona meses con informacion.')
    else:
        nacional = m.loc[m.mercado.eq('Nacional'), 'visitantes'].sum()
        extranjero = m.loc[m.mercado.eq('Extranjero'), 'visitantes'].sum()
        sin_pais = m.loc[m.mercado.eq('No informado'), 'visitantes'].sum()
        c1,c2,c3 = st.columns(3)
        c1.metric('Guatemala (nacional)', f'{nacional:,.0f}')
        c2.metric('Paises extranjeros (suma de categorias)', f'{extranjero:,.0f}')
        c3.metric('Pais no informado', f'{sin_pais:,.0f}')
        st.warning('Nacionales y extranjeros pueden tener factores de expansion diferentes. No comparar sus magnitudes como si fueran estimaciones homogeneas; no sumar poligonos.')
        top = top_mercados(mercados, sub, periodos)
        if top.empty:
            st.info('Sin paises extranjeros para esta seleccion.')
        else:
            fig4 = px.bar(top.sort_values('visitantes'), x='visitantes', y='pais', orientation='h',
                          labels={'visitantes':'Visitantes estimados de la categoria','pais':'Pais'})
            st.plotly_chart(aplicar_tema(fig4, 'Top 10 paises extranjeros del poligono'), width='stretch')
            st.caption('Suma temporal descriptiva de registros agregados por pais dentro de un poligono; no equivale a visitantes unicos del periodo. No se exportan microdatos.')
aviso_metodologico()
