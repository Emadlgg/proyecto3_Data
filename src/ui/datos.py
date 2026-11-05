"""Lectura defensiva de fuentes agregadas para la página de inicio."""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / 'data' / 'processed'


def leer_csv(nombre: str, raiz: Path = DATA) -> pd.DataFrame:
    ruta = Path(raiz) / nombre
    if not ruta.is_file():
        return pd.DataFrame()
    try:
        return pd.read_csv(ruta)
    except (OSError, ValueError, pd.errors.ParserError, UnicodeError):
        return pd.DataFrame()


def panorama(raiz: Path = DATA) -> dict:
    mov = leer_csv('movilidad_mensual_peten.csv', raiz)
    tikal = leer_csv('tikal_mensual.csv', raiz)
    ocupacion = leer_csv('ocupacion_peten.csv', raiz)
    perfil = leer_csv('encuestas/perfil_muestra.csv', raiz)
    datos = {'subdestinos': None, 'meses_movilidad': None, 'tikal_ultimo': None,
             'tikal_fecha': None, 'ocupacion_ultima': None, 'encuesta_disponible': not perfil.empty,
             'movilidad': mov, 'tikal': tikal}
    if {'fecha', 'subdestino'}.issubset(mov.columns):
        fechas = pd.to_datetime(mov['fecha'], errors='coerce').dropna()
        datos['subdestinos'] = int(mov['subdestino'].dropna().nunique())
        datos['meses_movilidad'] = int(fechas.dt.to_period('M').nunique())
    if {'fecha', 'total'}.issubset(tikal.columns):
        t = tikal.copy()
        t['fecha'] = pd.to_datetime(t['fecha'], errors='coerce')
        t['total'] = pd.to_numeric(t['total'], errors='coerce')
        t = t.dropna(subset=['fecha', 'total']).sort_values('fecha')
        if not t.empty:
            datos['tikal_ultimo'] = float(t.iloc[-1]['total'])
            datos['tikal_fecha'] = t.iloc[-1]['fecha'].strftime('%Y-%m')
    if {'fecha', 'indice_ocupacion'}.issubset(ocupacion.columns):
        o = ocupacion.copy()
        o['fecha'] = pd.to_datetime(o['fecha'], errors='coerce')
        o['indice_ocupacion'] = pd.to_numeric(o['indice_ocupacion'], errors='coerce')
        o = o.dropna(subset=['fecha', 'indice_ocupacion']).sort_values('fecha')
        if not o.empty:
            datos['ocupacion_ultima'] = float(o.iloc[-1]['indice_ocupacion'])
    return datos
