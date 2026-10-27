"""Módulo 4: triangulación descriptiva de Tikal, AIMM y telefonía."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.visualizaciones_extra import leer, comparacion_indices

st.set_page_config(page_title='Monitor especializado | Petén', layout='wide')
st.title('Monitor especializado de Tikal y Flores')
st.caption('Tres fuentes independientes: boletos a Tikal, movimientos de pasajeros del AIMM y presencia estimada por telefonía.')

@st.cache_data
def cargar():
    return (leer('comparacion_fuentes_indices.csv'), leer('tikal_indicadores.csv'),
            leer('aimm_pasajeros_indicadores.csv'), leer('aimm_operaciones_indicadores.csv'))
try:
    comp, tik, air, ops = cargar()
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc)); st.stop()

st.info('Las fuentes miden universos diferentes. Los índices base 100 muestran cambios relativos; no equivalen a visitantes únicos ni pueden sumarse.')
st.subheader('Triangulación de las tres fuentes')
if comp.empty:
    st.warning('No existen meses coincidentes entre las tres fuentes.')
else:
    st.caption(f'Cobertura coincidente: {comp.fecha.min():%Y-%m} a {comp.fecha.max():%Y-%m}.')
    nombres = {'indice_boletos_tikal':'Tikal (boletos)', 'indice_pasajeros_aimm':'AIMM (pasajeros)',
               'indice_movilidad_poligono_aeropuerto':'Telefonía (polígono aeropuerto)'}
    disponibles = st.multiselect('Fuentes visibles', list(nombres), default=list(nombres), format_func=lambda x:nombres[x])
    d = comparacion_indices(comp)
    d = d.loc[d.fuente.isin(disponibles)]
    if d.empty:
        st.info('Selecciona al menos una fuente.')
    else:
        d['fuente'] = d.fuente.map(nombres)
        fig = px.line(d, x='fecha', y='indice', color='fuente', markers=True,
                      title='Evolución relativa (primer mes coincidente = 100)',
                      labels={'fecha':'Mes','indice':'Índice base 100'})
        fig.add_hline(y=100, line_dash='dash')
        st.plotly_chart(fig, use_container_width=True)
    mes = st.selectbox('Mes de detalle', sorted(comp.fecha.unique()),
                       format_func=lambda x:pd.Timestamp(x).strftime('%Y-%m'))
    fila = comp.loc[comp.fecha.eq(pd.Timestamp(mes))].iloc[0]
    c1,c2,c3 = st.columns(3)
    c1.metric('Boletos Tikal', f'{fila.boletos_tikal:,.0f}')
    c2.metric('Pasajeros AIMM', f'{fila.pasajeros_aimm:,.0f}')
    c3.metric('Telefonía: polígono aeropuerto', f'{fila.movilidad_poligono_aeropuerto:,.0f}')
    st.caption('Los tres valores corresponden a poblaciones y procedimientos distintos. La telefonía no equivale a pasajeros ni boletos.')
    with st.expander('Datos coincidentes y notas metodológicas'):
        st.dataframe(comp, hide_index=True)

st.subheader('Tikal: evolución de boletos')
t = tik.copy().sort_values('fecha')
cat = st.selectbox('Categoría de boletos', ['total','nacionales','extranjeros','otros'])
years = sorted(t.fecha.dt.year.unique())
ys = st.multiselect('Años de Tikal', years, default=years[-4:])
t = t.loc[t.fecha.dt.year.isin(ys)]
if t.empty:
    st.info('Selecciona al menos un año.')
else:
    fig2 = px.line(t, x='fecha', y=cat, markers=True, title=f'Boletos de Tikal: {cat}',
                   labels={'fecha':'Mes',cat:'Boletos'})
    st.plotly_chart(fig2, use_container_width=True)
    if t.loc[t.total.eq(0)].shape[0]:
        st.warning('Algunos meses de Tikal tienen total cero sin interpretación confirmada. No se atribuyen automáticamente a cierres.')

st.subheader('AIMM: pasajeros y operaciones (unidades separadas)')
flujos = sorted(air.flujo.dropna().unique())
filtro = st.multiselect('Flujo de pasajeros', flujos, default=flujos)
a = air.loc[air.flujo.isin(filtro)].copy()
a = a.groupby(['fecha','flujo'],as_index=False).pasajeros.sum()
if not a.empty:
    fig3 = px.line(a, x='fecha', y='pasajeros', color='flujo', title='Movimientos mensuales de pasajeros',
                   labels={'fecha':'Mes','pasajeros':'Movimientos de pasajeros'})
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info('Selecciona un flujo.')
oper = ops.groupby(['fecha','tipo_operacion'],as_index=False).operaciones.sum()
fig4 = px.line(oper, x='fecha', y='operaciones', color='tipo_operacion',
               title='Operaciones aeronáuticas (no pasajeros)',
               labels={'fecha':'Mes','operaciones':'Operaciones'})
st.plotly_chart(fig4, use_container_width=True)
st.caption('Las operaciones aeronáuticas no se representan en el mismo eje que los pasajeros. Las series del AIMM combinan fuentes con distinta desagregación según el período.')
