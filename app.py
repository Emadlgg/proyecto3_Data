"""Inicio del Observatorio Turístico de Petén."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado, aviso_metodologico, metrica_segura
from src.ui.datos import panorama
from src.ui.graficas import aplicar_tema

st.set_page_config(page_title='Observatorio turístico | Petén', page_icon='📊', layout='wide',
                   initial_sidebar_state='expanded')
aplicar_estilos()

st.sidebar.markdown('### Observatorio de Petén')
st.sidebar.caption('Tikal · Flores · El Remate · AIMM')
st.sidebar.markdown('Selecciona un módulo desde la navegación de Streamlit.')
st.sidebar.divider()
st.sidebar.caption('Proyecto académico · Datos institucionales de uso restringido')

encabezado('Observatorio de Inteligencia Turística',
           'Panorama de Tikal, Flores y otros subdestinos de Petén. '
           'Explora demanda, temporalidad, hotelería, fuentes complementarias y perfil del visitante.',
           'Archivos procesados de INGUAT y fuentes del proyecto')

@st.cache_data(show_spinner=False)
def cargar_panorama():
    return panorama()

p = cargar_panorama()
a, b, c = st.columns(3)
with a:
    metrica_segura('Subdestinos con movilidad', p['subdestinos'])
with b:
    metrica_segura('Meses de movilidad observada', p['meses_movilidad'])
with c:
    metrica_segura('Último registro mensual de Tikal', p['tikal_ultimo'])
    if p['tikal_fecha']:
        st.caption(f"Período: {p['tikal_fecha']}. Boletos registrados; no visitantes únicos de Petén.")

st.subheader('Evolución de la movilidad por subdestino')
mov = p['movilidad']
if {'fecha', 'subdestino', 'segmento', 'visitantes'}.issubset(mov.columns) and not mov.empty:
    d = mov.copy()
    d['fecha'] = pd.to_datetime(d['fecha'], errors='coerce')
    d['visitantes'] = pd.to_numeric(d['visitantes'], errors='coerce')
    d = d.dropna(subset=['fecha', 'visitantes'])
    opciones = sorted(d['subdestino'].dropna().unique().tolist())
    elegidos = st.multiselect('Subdestinos', opciones, default=opciones, key='home_subdestinos')
    d = d[d['subdestino'].isin(elegidos)]
    if not d.empty:
        # Agregar segmentos dentro de cada subdestino; nunca sumar subdestinos.
        serie = d.groupby(['fecha', 'subdestino'], as_index=False)['visitantes'].sum()
        fig = px.line(serie, x='fecha', y='visitantes', color='subdestino', markers=True,
                      labels={'fecha': 'Mes', 'visitantes': 'Movimientos estimados por telefonía',
                              'subdestino': 'Subdestino'})
        st.plotly_chart(aplicar_tema(fig, 'Movilidad mensual observada por subdestino'), width='stretch')
        st.caption('Cada línea representa su propio polígono de movilidad. No sumar líneas para obtener visitantes únicos.')
    else:
        st.info('Selecciona al menos un subdestino.')
else:
    st.warning('No se encontró la serie de movilidad procesada. Ejecuta el ETL antes de iniciar el dashboard.')

aviso_metodologico()
st.subheader('Explora los módulos')
modulos = [
    ('Demanda turística', 'Movilidad, segmentación y estadía.', 'pages/1_Demanda.py'),
    ('Temporalidad y predicciones', 'Patrones diarios, evaluación y publicación.', 'pages/2_Temporalidad.py'),
    ('Hotelería', 'Ocupación e inventario de alojamiento.', 'pages/3_Hoteleria.py'),
    ('Monitor especializado', 'Tikal, AIMM y telefonía en períodos comparables.', 'pages/4_Monitor_Peten.py'),
    ('Perfil del visitante', 'Encuesta descriptiva sin expansión poblacional.', 'pages/5_Perfil_Visitante.py'),
]
for izquierda, derecha in [(0, 1), (2, 3)]:
    cols = st.columns(2)
    for col, i in zip(cols, (izquierda, derecha)):
        nombre, desc, pagina = modulos[i]
        with col:
            with st.container(border=True):
                st.markdown(f'**{nombre}**')
                st.caption(desc)
                if Path(pagina).exists():
                    st.page_link(pagina, label='Abrir módulo')
                else:
                    st.caption('Próximamente')
with st.container(border=True):
    st.markdown('**Perfil del visitante**')
    st.caption('Resultados descriptivos de la encuesta de visitantes; sin expansión poblacional.')
    if Path(modulos[4][2]).exists():
        st.page_link(modulos[4][2], label='Abrir módulo')
    else:
        st.caption('La página se incorporará en la siguiente entrega.')

st.divider()
st.caption('Observatorio académico de Petén · No publicar datos institucionales sin autorización. '
           'Las predicciones no aprobadas no constituyen cifras oficiales.')
