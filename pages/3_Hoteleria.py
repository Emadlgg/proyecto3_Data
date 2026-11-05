"""Hotelería de Petén: ocupación, inventarios y cruces descriptivos."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado
from src.ui.graficas import aplicar_tema
from src.ui.analitica import cargar, datos_disponibles
from src.visualizaciones_extra import ocupacion_y_afluencia

st.set_page_config(page_title="Hotelería | Petén", layout="wide")
aplicar_estilos()
encabezado(
    "Oferta hotelera",
    "Capacidad instalada, ocupación y contexto territorial de Petén.",
    "Fuentes distintas: inventario hotelero, ocupación, Tikal y movilidad telefónica",
)

@st.cache_data(show_spinner=False)
def datos():
    return (
        cargar("indicadores/ocupacion_indicadores.csv"),
        cargar("indicadores/capacidad_hotelera.csv"),
        cargar("indicadores/tikal_indicadores.csv"),
        cargar("indicadores/visitantes_subdestino.csv"),
    )

def inventario_anual(oferta: pd.DataFrame) -> pd.DataFrame:
    """Selecciona el ultimo corte por anio y tipo sin acumular trimestres.

    Rechaza duplicados cuando no hay columna que permita ordenar cortes.
    """
    requeridas = {"anio", "tipo_alojamiento", "establecimientos", "habitaciones", "plazas_cama"}
    if oferta.empty or not requeridas.issubset(oferta.columns):
        return pd.DataFrame(columns=sorted(requeridas))
    d = oferta.copy()
    d["anio"] = pd.to_numeric(d["anio"], errors="coerce")
    d = d.loc[d["anio"].between(2022, 2025)].copy()
    claves = ["anio", "tipo_alojamiento"]
    if "trimestre" in d.columns:
        d["orden_corte"] = pd.to_numeric(
            d["trimestre"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
        )
        if d["orden_corte"].isna().any() or not d["orden_corte"].between(1, 4).all():
            raise ValueError("Inventario: trimestre invalido o ausente")
        if d.duplicated(claves + ["orden_corte"]).any():
            raise ValueError("Inventario: cortes duplicados para el mismo anio y tipo")
        d = d.sort_values("orden_corte").drop_duplicates(claves, keep="last")
    elif d.duplicated(claves).any():
        raise ValueError("Inventarios duplicados sin columna 'trimestre'; revisar fuente")
    return d.sort_values(claves).reset_index(drop=True)


def comparacion_poligonos(visitantes: pd.DataFrame, fecha) -> pd.DataFrame:
    """Devuelve cada poligono por separado, nunca un total de Peten."""
    columnas = ["fecha", "subdestino", "visitantes"]
    if visitantes.empty or not set(columnas).issubset(visitantes.columns):
        return pd.DataFrame(columns=columnas)
    d = visitantes[columnas].copy()
    d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce")
    d["visitantes"] = pd.to_numeric(d["visitantes"], errors="coerce")
    d = d.loc[d["fecha"].eq(pd.Timestamp(fecha))].copy()
    if d.duplicated(["fecha", "subdestino"]).any():
        raise ValueError("Duplicados por fecha y subdestino en indicadores")
    return d.dropna(subset=["visitantes"]).sort_values("subdestino").reset_index(drop=True)


ocup, oferta, tik, mov = datos()
if not datos_disponibles(ocup, ["fecha", "ocupacion_pct"]) or not datos_disponibles(
    oferta, ["anio", "tipo_alojamiento", "establecimientos", "habitaciones", "plazas_cama"]
):
    st.error("Faltan indicadores hoteleros. Ejecuta python -m src.indicadores.")
    st.stop()

st.subheader("Ocupación hotelera mensual · 2023–2025")
ocup = ocup.copy()
ocup["ocupacion_pct"] = pd.to_numeric(ocup["ocupacion_pct"], errors="coerce")
ocup = ocup.loc[ocup.fecha.dt.year.between(2023, 2025)].dropna(subset=["fecha", "ocupacion_pct"])
anios = sorted(ocup.fecha.dt.year.unique().tolist())
seleccion = st.multiselect("Años de ocupación", anios, default=anios)
d = ocup.loc[ocup.fecha.dt.year.isin(seleccion)].sort_values("fecha")
if d.empty:
    st.info("Selecciona al menos un año con datos.")
else:
    ultimo = d.iloc[-1]
    st.metric("Última ocupación del período seleccionado", f"{ultimo.ocupacion_pct:.1f}%")
    fig = px.line(d, x="fecha", y="ocupacion_pct", markers=True,
                  labels={"fecha": "Mes", "ocupacion_pct": "Ocupación (%)"})
    fig.update_yaxes(range=[0, 100])
    st.plotly_chart(aplicar_tema(fig, "Evolución mensual de la ocupación"), width="stretch")
st.caption("Porcentaje de ocupación departamental; no representa visitantes únicos.")

st.divider()
st.subheader("Capacidad instalada · evolución anual 2022–2025")
st.caption("Establecimientos, habitaciones y plazas cama son inventarios al corte; no se suman trimestres.")
tipos = sorted(oferta.tipo_alojamiento.dropna().unique().tolist())
elegidos = st.multiselect("Tipos de alojamiento", tipos, default=tipos)
metrica = st.selectbox("Indicador de capacidad", ["establecimientos", "habitaciones", "plazas_cama"],
                       format_func=lambda x: x.replace("_", " ").capitalize())
try:
    inventario = inventario_anual(oferta.loc[oferta.tipo_alojamiento.isin(elegidos)])
except ValueError as exc:
    st.error(str(exc))
    inventario = pd.DataFrame()
if inventario.empty:
    st.info("No hay inventario para la selección.")
else:
    inventario["anio_etiqueta"] = inventario.anio.astype(int).astype(str)
    fig = px.bar(inventario, x="anio_etiqueta", y=metrica, color="tipo_alojamiento",
                 barmode="stack", labels={"anio_etiqueta": "Año", "tipo_alojamiento": "Tipo",
                                          metrica: "Inventario al corte"})
    st.plotly_chart(aplicar_tema(fig, f"{metrica.replace('_', ' ').capitalize()} por año y tipo"), width="stretch")
    st.caption("La suma entre tipos corresponde solo al inventario del mismo corte anual; verificar comparabilidad de cortes.")
    with st.expander("Ver inventario anual"):
        st.dataframe(inventario[["anio", "tipo_alojamiento", metrica]], hide_index=True, width="stretch")
st.info("Los registros de 2026 son parciales y no se incluyen en la comparación anual 2022–2025.")

st.divider()
st.subheader("Ocupación y afluencia · ventana coincidente sep–dic 2025")
if datos_disponibles(tik, ["fecha", "total"]):
    cruce = ocupacion_y_afluencia(ocup, tik)
    if cruce.empty:
        st.info("No hay meses coincidentes para este cruce.")
    else:
        cruce = cruce.copy()
        cruce["mes_etiqueta"] = pd.to_datetime(cruce["fecha"]).dt.strftime("%Y-%m")
        fig = px.scatter(
            cruce, x="boletos_tikal", y="ocupacion_pct", text="mes_etiqueta",
            hover_data={"mes_etiqueta": True, "fecha": False},
            labels={"boletos_tikal": "Boletos Tikal", "ocupacion_pct": "Ocupación (%)"},
        )
        fig.update_traces(textposition="top center", marker=dict(size=12))
        fig.update_layout(margin=dict(t=75, b=50))
        st.plotly_chart(aplicar_tema(fig, "Boletos Tikal y ocupación hotelera (cuatro meses)"), width="stretch")
        st.caption("Comparación descriptiva: boletos de Tikal y ocupación hotelera miden universos diferentes. No demuestra causalidad.")
else:
    st.info("No hay indicadores de Tikal para realizar el cruce.")

st.divider()
st.subheader("Comparación territorial · polígonos individuales")
if datos_disponibles(mov, ["fecha", "subdestino", "visitantes"]):
    meses = sorted(pd.to_datetime(mov.fecha.dropna().unique()))
    if meses:
        mes = st.selectbox("Mes de movilidad", meses, index=len(meses)-1,
                           format_func=lambda x: pd.Timestamp(x).strftime("%Y-%m"))
        territorios = comparacion_poligonos(mov, mes)
        if not territorios.empty:
            fig = px.bar(territorios, x="subdestino", y="visitantes",
                         labels={"subdestino": "Polígono", "visitantes": "Visitantes estimados del polígono"})
            st.plotly_chart(aplicar_tema(fig, "Afluencia relativa por polígono"), width="stretch")
            st.caption("Cada polígono se interpreta individualmente; no se suman para obtener visitantes únicos de Petén.")
        else:
            st.info("Sin datos para el mes seleccionado.")
else:
    st.info("Ejecuta python -m src.indicadores para mostrar la comparación territorial.")
