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


def consumir_seleccion(estado, clave: str, valor):
    """Procesa una selección de gráfica una sola vez.

    Las selecciones de Plotly en Streamlit persisten entre ejecuciones. Si se reaplican en cada
    rerun, una selección vieja pisa lo que la persona eligió después en otros controles.
    Devuelve ``valor`` solo cuando es nuevo; ``None`` si no hay selección o ya se procesó.
    ``estado`` es ``st.session_state`` (o cualquier dict).
    """
    if valor is None:
        estado[clave] = None
        return None
    if estado.get(clave) == valor:
        return None
    estado[clave] = valor
    return valor


def completar_calendario(df: pd.DataFrame, fecha: str = 'fecha', grupos=(), freq: str = 'MS') -> pd.DataFrame:
    """Inserta filas vacías (NaN) para los períodos sin observación.

    Sirve para que las líneas se corten en los huecos en lugar de unir con una recta los puntos
    vecinos: la ausencia de dato no es cero ni se interpola. Requiere una fila por fecha (y grupo);
    agregue antes si hace falta. El rango se calcula por grupo, sin extrapolar fuera de lo observado.
    """
    if df.empty or fecha not in df.columns:
        return df.copy()
    d = df.copy()
    d[fecha] = pd.to_datetime(d[fecha], errors='coerce').dt.normalize()
    d = d.dropna(subset=[fecha])
    grupos = list(grupos)
    if d.duplicated([fecha] + grupos).any():
        raise ValueError('completar_calendario: hay fechas duplicadas; agregue antes de completar')

    def _completa(g):
        idx = pd.date_range(g[fecha].min(), g[fecha].max(), freq=freq)
        return g.set_index(fecha).reindex(idx).rename_axis(fecha).reset_index()

    if not grupos:
        return _completa(d)
    partes = []
    for clave, g in d.groupby(grupos, sort=True):
        valores = clave if isinstance(clave, tuple) else (clave,)
        g = _completa(g.drop(columns=grupos))
        for c, v in zip(grupos, valores):
            g[c] = v
        partes.append(g)
    return pd.concat(partes, ignore_index=True)[list(d.columns)]


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


def ultimo_candidato(root: Path = ROOT / 'artifacts') -> dict | None:
    """Resumen del candidato más reciente evaluado por el pipeline (aprobado o no).

    Solo lectura: no publica ni modifica nada. Devuelve None si no hay ejecuciones legibles.
    """
    runs = Path(root) / 'runs'
    if not runs.is_dir():
        return None
    for carpeta in sorted((c for c in runs.iterdir() if c.is_dir()), reverse=True):
        try:
            rec = json.loads((carpeta / 'ejecucion.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict):
            continue
        dec = rec.get('decision') if isinstance(rec.get('decision'), dict) else {}
        return {
            'run_id': rec.get('run_id', carpeta.name),
            'estado': rec.get('estado', 'DESCONOCIDO'),
            'inicio_utc': rec.get('inicio_utc'),
            'aprobado': dec.get('aprobado'),
            'razon': dec.get('razon'),
            'mae_modelo': dec.get('MAE_modelo'),
            'mae_referencia': dec.get('MAE_referencia'),
            'ratio_mae': dec.get('ratio_mae'),
            'umbral_ratio': dec.get('umbral_ratio'),
            'publicado': bool(rec.get('publicado', False)),
            'errores': rec.get('errores') or [],
        }
    return None
