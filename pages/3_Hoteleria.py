"""Módulo 3: ocupación y capacidad hotelera, sin acumular inventarios."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.visualizaciones_extra import leer, ocupacion_y_afluencia

st.set_page_config(page_title='Oferta hotelera | Petén', layout='wide')
st.title('Oferta hotelera y desagregación territorial')
st.caption('La ocupación es un porcentaje mensual; establecimientos, habitaciones y plazas cama son inventarios al corte.')

@st.cache_data
def cargar():
    return (leer('ocupacion_indicadores.csv'), leer('capacidad_hotelera.csv'),
            leer('tikal_indicadores.csv'), leer('visitantes_subdestino.csv'))
try:
    ocup, oferta, tik, sub = cargar()
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc)); st.stop()

st.subheader('Ocupación hotelera')
anios = sorted(ocup.fecha.dt.year.unique())
sel_anios = st.multiselect('Años de ocupación', anios, default=anios)
d = ocup.loc[ocup.fecha.dt.year.isin(sel_anios)].sort_values('fecha')
if d.empty:
    st.info('Selecciona algún año.')
else:
    fig = px.line(d, x='fecha', y='ocupacion_pct', markers=True, title='Tasa mensual de ocupación hotelera de Petén',
                  labels={'fecha':'Mes','ocupacion_pct':'Ocupación (%)'})
    fig.update_yaxes(range=[0,100])
    st.plotly_chart(fig, use_container_width=True)

st.subheader('Capacidad instalada')
st.info('Cada fila es un inventario en una fecha de corte. No se suman trimestres ni se anualiza 2026 parcial.')
cols = ['establecimientos','habitaciones','plazas_cama']
metrica = st.selectbox('Indicador de capacidad', cols, format_func=lambda x: x.replace('_',' ').capitalize())
tipos = sorted(oferta.tipo_alojamiento.dropna().unique())
tipos_sel = st.multiselect('Tipo de alojamiento', tipos, default=tipos)
inv = oferta.loc[oferta.tipo_alojamiento.isin(tipos_sel)].copy()
inv['corte'] = inv.anio.astype(str) + '-T' + inv.trimestre.astype(str)
if inv.empty:
    st.info('No hay inventario para los tipos seleccionados.')
else:
    fig2 = px.bar(inv, x='corte', y=metrica, color='tipo_alojamiento', barmode='group',
                  title='Inventario por corte y tipo de alojamiento',
                  labels={'corte':'Corte de inventario', metrica:metrica.replace('_',' ').capitalize()})
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(inv[['anio','trimestre','tipo_alojamiento',metrica]], hide_index=True)

st.subheader('Ventana coincidente: septiembre–diciembre de 2025')
cruce = ocupacion_y_afluencia(ocup, tik)
if cruce.empty:
    st.info('No hay meses coincidentes para ocupación y Tikal.')
else:
    fig3 = px.scatter(cruce, x='boletos_tikal', y='ocupacion_pct', text=cruce.fecha.dt.strftime('%Y-%m'),
                      title='Boletos de Tikal frente a ocupación hotelera (4 meses)',
                      labels={'boletos_tikal':'Boletos de Tikal','ocupacion_pct':'Ocupación (%)'})
    fig3.update_traces(textposition='top center', marker={'size':13})
    st.plotly_chart(fig3, use_container_width=True)
    st.caption('Cruce descriptivo de cuatro meses. No permite atribuir cambios de ocupación a los boletos de Tikal ni inferir causalidad.')

st.subheader('Comparación entre subdestinos')
subs = sorted(sub.subdestino.dropna().unique())
meses = sorted(sub.fecha.dropna().unique())
mes = st.selectbox('Mes de telefonía', meses, index=len(meses)-1, format_func=lambda x:pd.Timestamp(x).strftime('%Y-%m'))
sel = sub.loc[sub.fecha.eq(pd.Timestamp(mes)) & sub.subdestino.isin(subs)].copy()
fig4 = px.bar(sel, x='subdestino', y='visitantes', title='Visitantes por polígono en el mes seleccionado',
              labels={'subdestino':'Polígono','visitantes':'Visitantes del polígono'})
st.plotly_chart(fig4, use_container_width=True)
st.caption('Los polígonos pueden solaparse. No se suman para calcular visitantes únicos de Petén.')
