"""Módulo 1: demanda turística por subdestino de Petén."""
import streamlit as st
from src.visualizaciones import (leer_csv, serie_subdestinos, estadia_subdestinos,
                                 segmentos, participacion)

st.set_page_config(page_title='Demanda turística | Petén', layout='wide')
st.title('Demanda turística y subdestinos')
st.caption('Datos de telefonía. Las cifras se refieren a cada polígono y pueden incluir personas presentes en más de uno.')

@st.cache_data

def cargar():
    return (leer_csv('visitantes_subdestino.csv'),
            leer_csv('estadia_ponderada.csv'),
            leer_csv('segmentacion_visitantes.csv'))

try:
    visitantes, estadia, seg = cargar()
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

subdestinos = sorted(visitantes['subdestino'].dropna().unique().tolist())
meses = sorted(visitantes['fecha'].dropna().unique().tolist())
if not subdestinos or not meses:
    st.warning('No hay registros disponibles.')
    st.stop()

seleccion = st.sidebar.multiselect('Subdestinos', subdestinos, default=subdestinos)
mes = st.sidebar.selectbox('Mes de detalle', meses, index=len(meses)-1,
                           format_func=lambda x: str(x)[:7])
visibles = st.sidebar.multiselect('Gráficas visibles',
    ['Evolución de visitantes', 'Estadía ponderada', 'Turistas y excursionistas', 'Composición por subdestino'],
    default=['Evolución de visitantes', 'Estadía ponderada', 'Turistas y excursionistas', 'Composición por subdestino'])
if not seleccion:
    st.warning('Selecciona al menos un subdestino.')
    st.stop()

v = visitantes[visitantes.subdestino.isin(seleccion)]
e = estadia[estadia.subdestino.isin(seleccion)]
s = seg[seg.subdestino.isin(seleccion)]

st.info('Los filtros de subdestino y mes enlazan las vistas. El selector de mes modifica la composición detallada; no se suman polígonos.')
if 'Evolución de visitantes' in visibles:
    st.plotly_chart(serie_subdestinos(v), use_container_width=True)
if 'Estadía ponderada' in visibles:
    st.plotly_chart(estadia_subdestinos(e), use_container_width=True)
if 'Turistas y excursionistas' in visibles:
    detalle = st.selectbox('Subdestino para segmentación', seleccion)
    st.plotly_chart(segmentos(s, detalle), use_container_width=True)
if 'Composición por subdestino' in visibles:
    st.plotly_chart(participacion(s, mes), use_container_width=True)
st.caption('Estadía = suma de días-persona / suma de visitantes, exclusivamente para el segmento con pernocta. Los excursionistas no entran en ese promedio.')
