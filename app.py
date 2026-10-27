"""Página inicial del Observatorio de Inteligencia Turística de Petén."""
import streamlit as st

st.set_page_config(page_title='Observatorio turístico | Petén', page_icon='🌿', layout='wide')
st.title('Observatorio de Inteligencia Turística')
st.subheader('Tikal y Flores, Petén')
st.write('Panel académico de apoyo a decisiones turísticas, basado en fuentes institucionales procesadas.')
st.info('Las fuentes tienen diferentes unidades y poblaciones. No se suman los subdestinos para obtener visitantes únicos de Petén.')
st.markdown('### Navegación')
st.write('Utiliza el menú lateral para abrir **Demanda turística**. Los módulos de temporalidad, hotelería y monitor especializado se incorporarán en las siguientes etapas.')
st.markdown('### Estado de la información')
st.write('Los datos observados y las estimaciones se presentarán por separado. Enero y febrero de 2026 carecen de cobertura telefónica observada.')
st.caption('Repositorio académico: https://github.com/Emadlgg/proyecto3_Data.git · Mantener los datos institucionales fuera de repositorios públicos.')
