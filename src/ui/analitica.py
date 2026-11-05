"""Preparación segura de vistas analíticas. No mezcla universos ni publica candidatos."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data' / 'processed'


def cargar(relativa: str, base: Path = DATA) -> pd.DataFrame:
    """Carga CSV procesado sin crear datos ficticios ante ausencias."""
    path = Path(base) / relativa
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if 'fecha' in df:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    return df


def datos_disponibles(df: pd.DataFrame, columnas) -> bool:
    return not df.empty and set(columnas).issubset(df.columns)


def serie_poligonos(df: pd.DataFrame, seleccion) -> pd.DataFrame:
    """Suma segmentos dentro de un polígono, jamás polígonos entre sí."""
    if not datos_disponibles(df, ('fecha','subdestino','visitantes')):
        return pd.DataFrame(columns=['fecha','subdestino','visitantes'])
    d = df.loc[df.subdestino.isin(seleccion)].copy()
    return d.groupby(['fecha','subdestino'], as_index=False)['visitantes'].sum().sort_values('fecha')


def detalle_mes(df: pd.DataFrame, mes, subdestinos) -> pd.DataFrame:
    if not datos_disponibles(df, ('fecha','subdestino')):
        return df.iloc[0:0].copy()
    return df.loc[df.fecha.eq(pd.Timestamp(mes)) & df.subdestino.isin(subdestinos)].copy()


def filtrar_encuesta(df: pd.DataFrame, lugares, tipos) -> pd.DataFrame:
    if not datos_disponibles(df, ('Lugar_Turistico','tipo_visitante')):
        return df.iloc[0:0].copy()
    return df.loc[df.Lugar_Turistico.isin(lugares) & df.tipo_visitante.isin(tipos)].copy()


def resumen_encuesta(df: pd.DataFrame, indicador: str) -> pd.DataFrame:
    """Agrega recuentos y recalcula base; nunca promedia porcentajes."""
    if not datos_disponibles(df, ('indicador','respuesta','n_respuestas')):
        return pd.DataFrame(columns=['respuesta','n_respuestas','porcentaje_muestra','base_valida'])
    d = df.loc[df.indicador.eq(indicador)].copy()
    if d.empty:
        return pd.DataFrame(columns=['respuesta','n_respuestas','porcentaje_muestra','base_valida'])
    counts = d.groupby('respuesta', as_index=False)['n_respuestas'].sum()
    base = counts.n_respuestas.sum()
    counts['base_valida'] = base
    counts['porcentaje_muestra'] = counts.n_respuestas / base * 100 if base > 0 else float('nan')
    return counts.sort_values('n_respuestas', ascending=False)


def resumen_satisfaccion(df: pd.DataFrame, variable: str) -> dict | None:
    """Pondera medias por número de respuestas, no por tamaño de grupos."""
    if not datos_disponibles(df, ('variable','n_respuestas','media_muestra','porcentaje_4_5')):
        return None
    d = df.loc[df.variable.eq(variable) & df.n_respuestas.gt(0)].copy()
    if d.empty:
        return None
    n = d.n_respuestas.sum()
    return {'n': int(n), 'media': float((d.media_muestra * d.n_respuestas).sum() / n),
            'porcentaje_4_5': float((d.porcentaje_4_5 * d.n_respuestas).sum() / n)}


def version_aprobada(root: Path = ROOT / 'artifacts'):
    """Devuelve (archivo, metadata) solo tras verificación de publicación."""
    try:
        from src.publicacion import consultar
    except ImportError:
        return None
    try:
        result = consultar(Path(root))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if result is None:
        return None
    archivo, meta = result
    if (not isinstance(meta, dict) or meta.get('demo_sintetica')
            or not meta.get('evaluacion', {}).get('aprobado', False)):
        return None
    return archivo, meta
