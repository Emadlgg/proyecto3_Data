"""Perfil descriptivo de la encuesta de Petén (muestra por cuotas, sin expansión)."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado
from src.ui.graficas import aplicar_tema
from src.ui.analitica import (
    cargar, datos_disponibles, filtrar_encuesta,
    resumen_encuesta, resumen_satisfaccion,
)

st.set_page_config(page_title="Perfil del visitante | Petén", layout="wide")
aplicar_estilos()
encabezado(
    "Perfil del visitante",
    "Perfil, experiencia y percepción de las personas encuestadas en Petén (2025).",
    "Encuesta por cuotas · sin expansión poblacional",
)
st.info(
    "Los porcentajes describen respuestas válidas de la muestra, no a todos los visitantes "
    "de Petén. La base puede variar entre preguntas por no respuesta o saltos del cuestionario."
)

@st.cache_data(show_spinner=False)
def datos():
    return (
        cargar("encuestas/perfil_muestra.csv"),
        cargar("encuestas/satisfaccion_muestra.csv"),
        cargar("encuestas/cobertura_encuesta.csv"),
    )

perfil, satisfaccion, cobertura = datos()
requeridas = ["Lugar_Turistico", "tipo_visitante", "indicador", "respuesta", "n_respuestas"]
if not datos_disponibles(perfil, requeridas):
    st.error("No se encontraron los indicadores procesados. Ejecuta `python -m src.encuestas`.")
    st.stop()

lugares = sorted(perfil["Lugar_Turistico"].dropna().astype(str).unique().tolist())
tipos = sorted(perfil["tipo_visitante"].dropna().astype(str).unique().tolist())
st.sidebar.header("Filtros de encuesta")
sel_lugares = st.sidebar.multiselect("Lugar turístico", lugares, default=lugares)
sel_tipos = st.sidebar.multiselect("Tipo de visitante", tipos, default=tipos)
if not sel_lugares or not sel_tipos:
    st.warning("Selecciona al menos un lugar y un tipo de visitante.")
    st.stop()

d = filtrar_encuesta(perfil, sel_lugares, sel_tipos)
s = filtrar_encuesta(satisfaccion, sel_lugares, sel_tipos) if not satisfaccion.empty else satisfaccion
if d.empty:
    st.warning("No hay respuestas disponibles para los filtros seleccionados.")
    st.stop()

# Los 500 cuestionarios son el tamaño de la muestra completa, no de cada filtro.
st.caption("Muestra original: 500 encuestas. Los conteos mostrados abajo dependen de los filtros y de cada pregunta.")

TITULOS = {
    "genero": "Género", "edad": "Edad", "region_residencia": "Región de residencia",
    "pais_residencia": "País de residencia", "motivo_principal": "Motivo principal del viaje",
    "transporte_llegada": "Transporte de llegada", "uso_hospedaje": "Uso de hospedaje",
    "recomendacion": "Recomendación", "percepcion_seguridad": "Percepción de seguridad",
}


def etiqueta(indicador):
    return TITULOS.get(indicador, str(indicador).replace("_", " ").capitalize())


def mostrar_perfil(indicador: str, clave: str):
    resumen = resumen_encuesta(d, indicador)
    if resumen.empty:
        st.info("No hay respuestas válidas para este indicador y los filtros seleccionados.")
        return
    base = int(resumen["base_valida"].iloc[0])
    if base <= 0:
        st.info("No hay base válida para calcular porcentajes.")
        return
    resumen = resumen.copy()
    resumen["respuesta"] = resumen["respuesta"].astype(str)
    resumen["porcentaje_muestra"] = pd.to_numeric(resumen["porcentaje_muestra"], errors="coerce")
    resumen = resumen.dropna(subset=["porcentaje_muestra"])
    a, b = st.columns(2)
    a.metric("Respuestas válidas", f"{base:,}")
    b.metric("Categorías", f"{len(resumen):,}")
    if resumen.empty:
        return
    grafica = resumen.head(15).sort_values("porcentaje_muestra")
    fig = px.bar(
        grafica, x="porcentaje_muestra", y="respuesta", orientation="h",
        text="porcentaje_muestra", hover_data={"n_respuestas": True, "base_valida": True},
        labels={"porcentaje_muestra": "Porcentaje de respuestas válidas (%)", "respuesta": "Respuesta"},
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.update_layout(margin=dict(l=12, r=65, t=60, b=20), height=max(310, 32 * len(grafica) + 115))
    fig.update_xaxes(range=[0, max(105, float(grafica["porcentaje_muestra"].max()) * 1.15)])
    st.plotly_chart(aplicar_tema(fig, etiqueta(indicador)), width="stretch", key=f"perfil_{clave}")
    if len(resumen) > 15:
        st.caption("La gráfica presenta las 15 categorías más frecuentes; la tabla conserva todas.")
    st.caption("Base: respuestas válidas de la pregunta en los grupos seleccionados. No se promedian porcentajes.")
    with st.expander("Ver tabla del indicador"):
        st.dataframe(resumen, width="stretch", hide_index=True)


tab_perfil, tab_experiencia, tab_cobertura = st.tabs(
    ["Perfil y viaje", "Satisfacción y percepción", "Cobertura y metodología"]
)

with tab_perfil:
    st.subheader("Características de la muestra")
    disponibles = set(d["indicador"].dropna().astype(str).unique())
    secciones = {
        "Perfil demográfico y procedencia": ["genero", "edad", "region_residencia", "pais_residencia"],
        "Características del viaje": ["motivo_principal", "transporte_llegada", "uso_hospedaje"],
    }
    for titulo, candidatos in secciones.items():
        opciones = [x for x in candidatos if x in disponibles]
        if not opciones:
            continue
        st.markdown(f"#### {titulo}")
        seleccionado = st.selectbox("Selecciona un indicador", opciones, format_func=etiqueta, key=f"selector_{titulo}")
        mostrar_perfil(seleccionado, titulo)
    otros = sorted(disponibles - {x for v in secciones.values() for x in v})
    if otros:
        with st.expander("Otros indicadores de la encuesta"):
            elegido = st.selectbox("Indicador", otros, format_func=etiqueta, key="otros_indicadores")
            mostrar_perfil(elegido, "otros")

with tab_experiencia:
    st.subheader("Satisfacción de las personas encuestadas")
    st.caption("Las medias y los porcentajes 4–5 se ponderan por respuestas válidas de cada grupo.")
    cols_sat = ["variable", "pregunta", "n_respuestas", "media_muestra", "porcentaje_4_5"]
    if datos_disponibles(s, cols_sat):
        opciones = s[["variable", "pregunta"]].dropna().drop_duplicates().sort_values("pregunta")
        if not opciones.empty:
            nombres = dict(zip(opciones["variable"], opciones["pregunta"]))
            variable = st.selectbox("Aspecto evaluado", list(nombres), format_func=lambda x: str(nombres[x]))
            stats = resumen_satisfaccion(s, variable)
            if stats and stats["n"] > 0:
                a, b, c = st.columns(3)
                a.metric("Respuestas válidas", f"{stats['n']:,}")
                b.metric("Media (escala 1–5)", f"{stats['media']:.2f}")
                c.metric("Respuestas 4–5", f"{stats['porcentaje_4_5']:.1f}%")
                st.progress(min(max(float(stats["porcentaje_4_5"]) / 100, 0.0), 1.0))
                st.caption("El porcentaje 4–5 no equivale a una tasa de satisfacción poblacional.")
            else:
                st.info("Esta pregunta no tiene respuestas válidas con los filtros actuales.")
        else:
            st.info("No hay preguntas de satisfacción disponibles.")
    else:
        st.info("No se encontraron indicadores de satisfacción procesados.")
    disponibles = set(d["indicador"].dropna().astype(str))
    percepciones = [x for x in ["percepcion_seguridad", "recomendacion"] if x in disponibles]
    if percepciones:
        st.markdown("#### Percepción y recomendación")
        seleccion = st.selectbox("Indicador de percepción", percepciones, format_func=etiqueta)
        mostrar_perfil(seleccion, "percepcion")

with tab_cobertura:
    st.subheader("Cobertura del cuestionario")
    st.write(
        "La cobertura describe el cuestionario completo, **no** los filtros activos de esta página. "
        "Las preguntas pueden tener distintos denominadores por saltos y no respuesta."
    )
    if datos_disponibles(cobertura, ["columna", "pregunta", "n_validas", "n_encuestados", "porcentaje_observado"]):
        q = st.text_input("Buscar pregunta o variable", "")
        tabla = cobertura.copy()
        if q.strip():
            mask = (tabla["pregunta"].astype(str).str.contains(q, case=False, regex=False, na=False)
                    | tabla["columna"].astype(str).str.contains(q, case=False, regex=False, na=False))
            tabla = tabla.loc[mask]
        st.dataframe(tabla, hide_index=True, width="stretch")
    else:
        st.info("No se encontró el archivo de cobertura de la encuesta.")
    st.markdown("#### Consideraciones metodológicas")
    st.write(
        "Encuesta de visitantes de Petén 2025, seleccionada por cuotas y sin factor de expansión. "
        "Los recuentos corresponden a respuestas, no a visitantes únicos estimados. "
        "No deben sumarse a datos de telefonía, boletos de Tikal ni pasajeros del AIMM."
    )
