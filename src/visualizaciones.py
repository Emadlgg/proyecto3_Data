"""Gráficas Plotly del observatorio. No calcula totales entre polígonos."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BASE = Path(__file__).resolve().parents[1]
PROCESSED = BASE / 'data' / 'processed'


def leer_csv(nombre, carpeta='indicadores'):
    ruta = PROCESSED / carpeta / nombre if carpeta else PROCESSED / nombre
    if not ruta.is_file():
        raise FileNotFoundError(f'No se encontró {ruta}. Ejecuta primero python -m src.indicadores')
    df = pd.read_csv(ruta)
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='raise')
    return df


def serie_subdestinos(df):
    """Una línea por polígono; nunca suma polígonos."""
    return px.line(df.sort_values('fecha'), x='fecha', y='visitantes', color='subdestino',
                   markers=True, title='Visitantes mensuales por subdestino',
                   labels={'fecha':'Mes', 'visitantes':'Visitantes del polígono', 'subdestino':'Subdestino'})


def estadia_subdestinos(df):
    return px.line(df.sort_values('fecha'), x='fecha', y='estadia_media_ponderada_dias',
                   color='subdestino', markers=True, title='Estadía media ponderada (solo pernocta)',
                   labels={'fecha':'Mes', 'estadia_media_ponderada_dias':'Días por visitante'})


def segmentos(df, subdestino):
    d = df.loc[df['subdestino'].eq(subdestino)].sort_values('fecha').copy()
    d = d[['fecha', 'turistas_pernocta', 'excursionistas']].melt(id_vars=['fecha'], value_vars=['turistas_pernocta','excursionistas'],
               var_name='segmento', value_name='visitantes')
    return px.bar(d, x='fecha', y='visitantes', color='segmento', barmode='stack',
                  title=f'Turistas y excursionistas — {subdestino}',
                  labels={'fecha':'Mes','visitantes':'Visitantes del polígono'})


def participacion(df, fecha):
    d = df.loc[df['fecha'].eq(pd.Timestamp(fecha))].copy()
    if d.empty:
        return go.Figure().update_layout(title='Sin datos para el mes seleccionado')
    d = d.melt(id_vars=['subdestino'], value_vars=['proporcion_turistas','proporcion_excursionistas'],
               var_name='segmento', value_name='proporcion')
    fig = px.bar(d, x='subdestino', y='proporcion', color='segmento', barmode='stack',
                 title='Composición de visitantes por subdestino',
                 labels={'subdestino':'Subdestino','proporcion':'Proporción'})
    fig.update_yaxes(tickformat='.0%', range=[0,1])
    return fig
