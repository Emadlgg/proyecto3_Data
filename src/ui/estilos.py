"""Estilos discretos y accesibles para Streamlit (paleta en src/ui/paleta.py)."""
import streamlit as st

from src.ui.paleta import PRIMARIO, FONDO_TARJETA, NEUTRO_CLARO, NEUTRO, TEXTO


def aplicar_estilos() -> None:
    st.markdown(f'''<style>
    .block-container {{max-width: 1200px; padding-top: 2rem; padding-bottom: 3rem;}}
    h1, h2, h3 {{letter-spacing: -.025em; color: {PRIMARIO};}}
    [data-testid="stMetric"] {{border: 1px solid {NEUTRO_CLARO}; border-left: 5px solid {PRIMARIO};
        border-radius: 10px; padding: 1rem 1.1rem; background: {FONDO_TARJETA};}}
    [data-testid="stMetricLabel"] {{font-weight: 600; color: {TEXTO};}}
    [data-testid="stSidebar"] {{border-right: 1px solid {NEUTRO_CLARO};}}
    .small-note {{font-size: .88rem; color: {NEUTRO};}}
    </style>''', unsafe_allow_html=True)
