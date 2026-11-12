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


MAX_FILAS_TABLA = 200


def tabla_segura(df, max_filas: int = MAX_FILAS_TABLA, **kwargs) -> None:
    """Muestra una tabla agregada sin ofrecer descarga masiva de datos.

    La guía prohíbe habilitar descargas masivas de microdatos. Esta función limita las filas
    visibles; el botón de descarga que Streamlit agrega a los dataframes se oculta con CSS
    en ``src/ui/estilos.py``.
    """
    kwargs.setdefault('hide_index', True)
    kwargs.setdefault('width', 'stretch')
    if len(df) > max_filas:
        st.caption(f'Se muestran las primeras {max_filas} de {len(df):,} filas. '
                   'El tablero no ofrece descarga de datos.')
        df = df.head(max_filas)
    st.dataframe(df, **kwargs)
