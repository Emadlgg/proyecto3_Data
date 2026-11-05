"""Elementos reutilizables de presentación."""
import streamlit as st


def encabezado(titulo: str, descripcion: str, fuente: str | None = None) -> None:
    st.title(titulo)
    st.write(descripcion)
    if fuente:
        st.caption(f'Fuente: {fuente}')


def aviso_metodologico() -> None:
    st.info('Las fuentes miden universos distintos: telefonía, boletos de Tikal, '
            'pasajeros del AIMM y encuestas no deben sumarse ni interpretarse '
            'como visitantes únicos de Petén.')


def metrica_segura(etiqueta: str, valor, unidad: str = '') -> None:
    if valor is None:
        st.metric(etiqueta, 'Sin datos')
    else:
        st.metric(etiqueta, f'{valor:,.0f}{unidad}')
