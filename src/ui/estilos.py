"""Estilos discretos y accesibles para Streamlit."""
import streamlit as st


def aplicar_estilos() -> None:
    st.markdown('''<style>
    .block-container {max-width: 1200px; padding-top: 2rem; padding-bottom: 3rem;}
    h1, h2, h3 {letter-spacing: -.025em;}
    [data-testid="stMetric"] {border: 1px solid #dedede; border-radius: 12px;
        padding: 1rem 1.1rem; background: #fafafa;}
    [data-testid="stMetricLabel"] {font-weight: 600;}
    [data-testid="stSidebar"] {border-right: 1px solid #e8e8e8;}
    .small-note {font-size: .88rem; color: #5d6269;}
    </style>''', unsafe_allow_html=True)
