"""Laboratorio 12: reconstrucción comparativa del dashboard nacional del Lab 10.

Ejecutar desde la raíz del repositorio:
    python -m streamlit run labs/lab12_powerbi/streamlit_comparacion/app.py

Lee exclusivamente los cinco CSV existentes en data/processed/.
No modifica datos ni entrena modelos.
"""
from __future__ import annotations

from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed"
FILES = {
    "total": "serie_mensual_total.csv",
    "vias": "serie_mensual_por_via.csv",
    "estacional": "indice_estacional.csv",
    "metricas": "final_metricas_modelos.csv",
    "pronostico": "final_pronostico_prueba_intervalo80.csv",
}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
COLORES_VIA = {"Aérea": "#1B329F", "Terrestre": "#777D87", "Marítima": "#E9793A"}

st.set_page_config(page_title="Lab 12 | Comparación Streamlit", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 1.8rem; max-width: 1400px;}
h1,h2,h3 {letter-spacing: -.02em;}
[data-testid="stMetric"] {padding: .75rem 1rem; border: 1px solid rgba(128,128,128,.22); border-radius: 12px;}
</style>""", unsafe_allow_html=True)


def normalizar(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c)).strip().casefold()


@st.cache_data(show_spinner=False)
def leer_archivos(base: str) -> dict[str, pd.DataFrame]:
    carpeta = Path(base)
    tablas = {}
    for clave, nombre in FILES.items():
        ruta = carpeta / nombre
        if not ruta.is_file():
            raise FileNotFoundError(f"No se encontró {ruta}")
        tablas[clave] = pd.read_csv(ruta, encoding="utf-8-sig")
    for clave in ("total", "vias", "pronostico"):
        tablas[clave]["fecha"] = pd.to_datetime(tablas[clave]["fecha"], errors="raise")
    total = tablas["total"]
    vias = tablas["vias"]
    est = tablas["estacional"]
    met = tablas["metricas"]
    pred = tablas["pronostico"]
    for nombre, df, columnas in [
        ("total", total, ["fecha", "viajeros"]),
        ("vías", vias, ["fecha", "Aérea", "Marítima", "Terrestre"]),
        ("estacional", est, ["mes", "indice_estacional"]),
        ("métricas", met, ["Modelo", "MAE", "RMSE"]),
        ("pronóstico", pred, ["fecha", "observado", "estimacion", "limite_inferior_80", "limite_superior_80"]),
    ]:
        faltan = set(columnas) - set(df.columns)
        if faltan:
            raise ValueError(f"En {nombre} faltan columnas: {sorted(faltan)}")
    for clave, columnas in {
        "total": ["viajeros"], "vias": ["Aérea", "Marítima", "Terrestre"],
        "estacional": ["indice_estacional"], "metricas": ["MAE", "RMSE"],
        "pronostico": ["observado", "estimacion", "limite_inferior_80", "limite_superior_80"],
    }.items():
        for columna in columnas:
            tablas[clave][columna] = pd.to_numeric(tablas[clave][columna], errors="raise")
    if total.fecha.duplicated().any() or vias.fecha.duplicated().any() or pred.fecha.duplicated().any():
        raise ValueError("Hay fechas duplicadas en una serie mensual; revisar datos originales.")
    if met.Modelo.duplicated().any():
        raise ValueError("Hay modelos duplicados en la tabla de métricas.")
    return tablas


try:
    t = leer_archivos(str(DATA))
except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"No se pudieron cargar los datos del Lab 10: {exc}")
    st.code(str(DATA))
    st.stop()

total = t["total"].sort_values("fecha").copy()
vias = t["vias"].sort_values("fecha").copy()
estacional = t["estacional"].copy()
metricas = t["metricas"].copy()
pronostico = t["pronostico"].sort_values("fecha").copy()
total["Anio"] = total.fecha.dt.year
total["MesNumero"] = total.fecha.dt.month
anios = sorted(total.Anio.unique().tolist())

st.sidebar.title("Observatorio · Lab 12")
pagina = st.sidebar.radio("Sección", ["Exploración nacional", "Modelos predictivos"], key="lab12_pagina")
st.sidebar.caption("Reconstrucción funcional de Streamlit para comparación con Power BI. No reemplaza el dashboard principal de Petén.")

if pagina == "Exploración nacional":
    st.title("Movimientos migratorios nacionales")
    st.caption("Laboratorio 12 · Mismos CSV nacionales utilizados en Power BI · Los movimientos no equivalen a turistas únicos.")
    st.sidebar.subheader("Filtros de exploración")
    seleccion_anio = st.sidebar.selectbox("Año para detalle", anios, index=anios.index(2025) if 2025 in anios else len(anios)-1, key="lab12_anio")
    vias_elegidas = st.sidebar.multiselect("Vías visibles", ["Aérea", "Terrestre", "Marítima"], default=["Aérea", "Terrestre", "Marítima"])
    anual = total.groupby("Anio", as_index=False)["viajeros"].sum()
    fig_anual = px.bar(anual, x="Anio", y="viajeros", title="1. Movimientos migratorios por año", labels={"Anio": "Año", "viajeros": "Movimientos"})
    fig_anual.update_traces(marker_color="#1B329F")
    fig_anual.update_xaxes(type="category")
    st.plotly_chart(fig_anual, use_container_width=True)
    st.caption("Selecciona un año en el panel lateral para consultar sus doce meses. Esta reconstrucción utiliza un selector explícito; Power BI usa interacción cruzada y drill-down.")

    d_anio = total.loc[total.Anio.eq(seleccion_anio)].copy()
    d_anio["Mes"] = d_anio.MesNumero.map(lambda n: MESES[n-1])
    fig_mes = px.bar(d_anio, x="Mes", y="viajeros", title=f"2. Detalle mensual · {seleccion_anio}", labels={"viajeros": "Movimientos", "Mes": "Mes"}, category_orders={"Mes": MESES})
    fig_mes.update_traces(marker_color="#1B329F")
    st.plotly_chart(fig_mes, use_container_width=True)
    st.metric(f"Total nacional {seleccion_anio}", f"{d_anio.viajeros.sum():,.2f}")
    if len(d_anio) != 12:
        st.warning(f"El año {seleccion_anio} contiene {len(d_anio)} meses observados; no es un año completo.")

    st.divider()
    st.subheader("Vías de ingreso")
    col1, col2 = st.columns(2)
    via_anio = vias.loc[vias.fecha.dt.year.eq(seleccion_anio)]
    totales_via = via_anio[["Aérea", "Terrestre", "Marítima"]].sum()
    with col1:
        if totales_via.sum() > 0:
            fig_dona = px.pie(names=totales_via.index, values=totales_via.values, hole=.55,
                              title=f"3. Composición por vía · {seleccion_anio}",
                              color=totales_via.index, color_discrete_map=COLORES_VIA)
            st.plotly_chart(fig_dona, use_container_width=True)
        else:
            st.info("No hay valores positivos para la composición del año.")
    with col2:
        st.markdown("**Movimientos por vía en el año seleccionado**")
        for via in ["Terrestre", "Aérea", "Marítima"]:
            st.metric(via, f"{totales_via[via]:,.2f}")
    if vias_elegidas:
        largo = vias.melt(id_vars="fecha", value_vars=vias_elegidas, var_name="Via", value_name="Viajeros")
        fig_vias = px.line(largo, x="fecha", y="Viajeros", color="Via", title="4. Evolución mensual por vía (serie histórica)",
                            color_discrete_map=COLORES_VIA, labels={"fecha": "Fecha", "Viajeros": "Movimientos"})
        st.plotly_chart(fig_vias, use_container_width=True)
    else:
        st.info("Selecciona al menos una vía para mostrar la evolución.")

    st.divider()
    a, b = st.columns(2)
    estacional["MesNumero"] = estacional.mes.map(lambda x: next((i for i, m in enumerate(MESES, 1) if normalizar(m) == normalizar(x)), np.nan))
    if estacional.MesNumero.isna().any():
        st.warning("Algunos meses del índice estacional no tienen abreviatura reconocida; revisar el CSV.")
    estacional = estacional.sort_values("MesNumero")
    with a:
        fig_est = px.bar(estacional, x="mes", y="indice_estacional", title="5. Índice estacional · base 100",
                         labels={"mes": "Mes", "indice_estacional": "Índice estacional"})
        fig_est.add_hline(y=100, line_dash="dash", line_color="#667085")
        fig_est.update_traces(marker_color="#1B329F")
        st.plotly_chart(fig_est, use_container_width=True)
    with b:
        variacion = total[["fecha", "viajeros"]].copy()
        variacion["variacion_interanual_pct"] = variacion.viajeros.div(variacion.viajeros.shift(12)).sub(1).mul(100)
        variacion.loc[variacion.viajeros.shift(12).le(0), "variacion_interanual_pct"] = np.nan
        fig_yoy = px.line(variacion, x="fecha", y="variacion_interanual_pct", title="6. Variación interanual mensual (%)",
                          labels={"fecha": "Fecha", "variacion_interanual_pct": "Variación (%)"})
        fig_yoy.add_hline(y=0, line_dash="dash", line_color="#667085")
        fig_yoy.update_traces(line_color="#1B329F")
        st.plotly_chart(fig_yoy, use_container_width=True)
    st.caption("El índice estacional es relativo (base 100). La variación interanual compara cada mes con el mismo mes del año previo.")

else:
    st.title("Modelos predictivos · Lab 10")
    st.caption("Resultados originales importados; no se reentrenan ni se sustituyen por modelos del Proyecto 3.")
    met_long = metricas.melt(id_vars="Modelo", value_vars=["MAE", "RMSE"], var_name="Métrica", value_name="Error")
    met_long["Modelo"] = pd.Categorical(met_long.Modelo, categories=metricas.sort_values("MAE").Modelo, ordered=True)
    fig_metricas = px.bar(met_long, x="Error", y="Modelo", color="Métrica", barmode="group", orientation="h",
                           title="7. Comparación de errores: MAE y RMSE",
                           color_discrete_map={"MAE": "#1B329F", "RMSE": "#E9793A"})
    fig_metricas.update_layout(yaxis={"categoryorder": "array", "categoryarray": list(metricas.sort_values("MAE", ascending=False).Modelo)})
    st.plotly_chart(fig_metricas, use_container_width=True)
    mejor = metricas.loc[metricas.MAE.idxmin()]
    st.metric("Modelo con menor MAE", str(mejor.Modelo), f"MAE {mejor.MAE:,.2f}", delta_color="off")
    st.caption("Los errores solo son comparables si los modelos fueron evaluados en el mismo conjunto de prueba.")

    fig = go.Figure()
    series = [
        ("observado", "Observado", "#1B329F", "solid"),
        ("estimacion", "Estimación", "#E9793A", "solid"),
        ("limite_inferior_80", "Límite inferior 80 %", "#8A8A8A", "dash"),
        ("limite_superior_80", "Límite superior 80 %", "#AFAFAF", "dash"),
    ]
    for col, label, color, dash in series:
        fig.add_trace(go.Scatter(x=pronostico.fecha, y=pronostico[col], mode="lines+markers", name=label,
                                 line={"color": color, "dash": dash}, marker={"size": 4}))
    fig.update_layout(title="8. Observado, estimado e intervalo predictivo del 80 %",
                      xaxis_title="Fecha mensual", yaxis_title="Movimientos", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    if pronostico.limite_inferior_80.lt(0).any():
        st.info("El intervalo original incluye límites inferiores negativos en algunos meses. Se conservan para reproducir fielmente los resultados del Lab 10; no representan movimientos posibles.")
    st.caption("La tabla de pronósticos no identifica un modelo por fila; no se atribuye la serie a un modelo específico sin documentación adicional.")
    with st.expander("Ver métricas originales"):
        st.dataframe(metricas, use_container_width=True, hide_index=True)

st.divider()
st.caption("Lab 12 · Comparación metodológica: Streamlit reconstruido frente a Power BI Desktop. Datos de migración nacional; no mezclar con indicadores territoriales de Petén.")
