from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Observatorio turístico | Tikal y Flores', layout='wide')
st.markdown('''<style>h1,h2,h3{color:#174B3A} .stApp{background:#F7FAF8}</style>''', unsafe_allow_html=True)
BASE = Path(__file__).parent / 'data'
@st.cache_data
def load():
    a=pd.read_csv(BASE/'serie_mensual_total.csv',parse_dates=['fecha'])
    b=pd.read_csv(BASE/'serie_mensual_por_via.csv',parse_dates=['fecha'])
    return a,b

a,b=load()
st.title('Observatorio de Inteligencia Turística | Tikal y Flores')
st.warning('PROTOTIPO: las dos gráficas muestran datos NACIONALES del Laboratorio 9, NO cifras de Tikal/Flores. No usar para conclusiones locales.')
st.caption('Avance individual | Osman de León | Laboratorio 10')
page=st.sidebar.radio('Navegación',['Monitor de demanda','Dinámica temporal','Oferta hotelera (pendiente)','Monitor Tikal/Flores (pendiente)'])
years=sorted(a.fecha.dt.year.unique().tolist())
selected=st.sidebar.slider('Intervalo de años',int(min(years)),int(max(years)),(int(min(years)),int(max(years))))
a=a[a.fecha.dt.year.between(*selected)]
b=b[b.fecha.dt.year.between(*selected)]
if page in ('Monitor de demanda','Dinámica temporal'):
    st.subheader('1. Evolución mensual de viajeros — Guatemala (nacional)')
    fig=px.line(a,x='fecha',y='viajeros',labels={'fecha':'Mes','viajeros':'Viajeros'},color_discrete_sequence=['#177E78'])
    fig.update_layout(hovermode='x unified')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('Zoom, desplazamiento y consulta por fecha disponibles en la gráfica. Serie nacional, no departamental.')
    st.subheader('2. Viajeros por vía de ingreso — Guatemala (nacional)')
    choices=st.multiselect('Seleccionar vías de ingreso',['Aérea','Marítima','Terrestre'],default=['Aérea','Marítima','Terrestre'])
    if choices:
        melted=b.melt(id_vars='fecha',value_vars=choices,var_name='Vía',value_name='Viajeros')
        fig2=px.line(melted,x='fecha',y='Viajeros',color='Vía',color_discrete_map={'Aérea':'#177E78','Marítima':'#D39A43','Terrestre':'#365E87'})
        fig2.update_layout(hovermode='x unified')
        st.plotly_chart(fig2,use_container_width=True)
    else:
        st.info('Seleccione al menos una vía para visualizar la comparación.')
    st.info('Próximo paso: sustituir por las fuentes autorizadas de Petén y enlazar gráficos mediante selección cruzada.')
else:
    st.info('Módulo planificado. Se habilitará cuando se incorporen las bases específicas de Petén.')
