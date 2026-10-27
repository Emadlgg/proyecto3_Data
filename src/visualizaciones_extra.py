"""Funciones compartidas de los módulos 2, 3 y 4; no altera datos."""
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'processed'


def leer(nombre, carpeta='indicadores', base=DATA):
    ruta = Path(base) / carpeta / nombre if carpeta else Path(base) / nombre
    if not ruta.is_file():
        raise FileNotFoundError(f'Falta {ruta}. Ejecuta primero los scripts ETL, indicadores y predicciones.')
    df = pd.read_csv(ruta)
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='raise')
    return df


def serie_diaria(df, subdestino, evento=None):
    d = df.loc[df.subdestino.eq(subdestino)].copy()
    if evento is not None:
        d = d.loc[d.evento.eq(evento)]
    d = d.groupby('fecha', as_index=False).presencias_diarias.sum().sort_values('fecha')
    return d


def patron_semanal(df):
    """Promedio por fecha, no suma de días para inferir personas únicas."""
    d = df.copy()
    d['dia_semana'] = d.fecha.dt.dayofweek
    out = d.groupby('dia_semana', as_index=False).presencias_diarias.mean()
    out['nombre'] = out.dia_semana.map(dict(enumerate(['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'])))
    return out


def lift_eventos(df):
    """Comparación descriptiva por día de semana, dentro de la muestra disponible.
    Se usa la categoría 'Regular' como referencia; sin ella se devuelve NaN.
    """
    d = df.copy()
    d['dia_semana'] = d.fecha.dt.dayofweek
    base = d.loc[d.evento.astype(str).str.strip().str.casefold().eq('regular')]
    refs = base.groupby('dia_semana').presencias_diarias.mean()
    eventos = d.loc[~d.evento.astype(str).str.strip().str.casefold().eq('regular')].copy()
    eventos['referencia'] = eventos.dia_semana.map(refs)
    eventos['lift_pct'] = np.where(eventos.referencia.gt(0),
                                   100 * (eventos.presencias_diarias / eventos.referencia - 1), np.nan)
    return eventos


def comparacion_indices(df):
    """Mantiene las tres series separadas; solo compara variación relativa."""
    cols = ['indice_boletos_tikal','indice_pasajeros_aimm','indice_movilidad_poligono_aeropuerto']
    d = df[['fecha', *cols]].melt(id_vars='fecha', value_vars=cols, var_name='fuente', value_name='indice')
    return d


def ocupacion_y_afluencia(ocupacion, tikal):
    """Cruce Sep-Dic 2025 sin sumar poblaciones ni extrapolar períodos."""
    a = ocupacion[['fecha','ocupacion_pct']].copy()
    b = tikal[['fecha','total']].rename(columns={'total':'boletos_tikal'})
    d = a.merge(b, on='fecha', how='inner', validate='one_to_one')
    return d.loc[(d.fecha >= '2025-09-01') & (d.fecha <= '2025-12-01')].sort_values('fecha')


def grafica_vacia(mensaje):
    fig = go.Figure()
    fig.add_annotation(text=mensaje, x=.5, y=.5, xref='paper', yref='paper', showarrow=False)
    fig.update_layout(height=300, xaxis={'visible':False}, yaxis={'visible':False})
    return fig
