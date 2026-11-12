"""Triangulación cuantitativa entre fuentes independientes de Petén.

Fuentes: boletos de Tikal, pasajeros del AIMM y telefonía (un polígono a la vez).
Reglas que respeta este módulo:
- Solo se comparan meses en que AMBAS fuentes tienen dato; la ausencia no es cero.
- Los ceros de Tikal pendientes de confirmar se tratan como sin dato.
- No se suman fuentes ni polígonos: cada serie conserva su propia unidad.
- Los índices base 100 comparan variaciones relativas, no niveles equivalentes.
No depende de Streamlit.
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
import pandas as pd

from src.ui.analitica import completar_calendario

FUENTES = {
    'boletos_tikal': 'Boletos Tikal',
    'pasajeros_aimm': 'Pasajeros AIMM',
    'telefonia': 'Telefonía (polígono)',
}


def fuentes_mensuales(tikal: pd.DataFrame, aimm: pd.DataFrame, movilidad: pd.DataFrame,
                      poligono: str) -> pd.DataFrame:
    """Una fila por mes (calendario completo) con una columna por fuente; NaN = sin dato.

    - Tikal: columna ``total``; los meses con total 0 se tratan como sin dato.
    - AIMM: suma de pasajeros de todos los flujos y tipos del mes (misma definición que el ETL).
    - Telefonía: visitantes del polígono elegido (suma de segmentos DENTRO del polígono).
    """
    t = tikal[['fecha', 'total']].copy()
    t['total'] = pd.to_numeric(t['total'], errors='coerce')
    t.loc[t['total'].eq(0), 'total'] = np.nan
    t = t.rename(columns={'total': 'boletos_tikal'})

    a = (aimm.assign(pasajeros=pd.to_numeric(aimm['pasajeros'], errors='coerce'))
         .groupby('fecha', as_index=False)['pasajeros'].sum(min_count=1)
         .rename(columns={'pasajeros': 'pasajeros_aimm'}))

    m = movilidad.loc[movilidad['subdestino'].eq(poligono)].copy()
    m['visitantes'] = pd.to_numeric(m['visitantes'], errors='coerce')
    m = (m.groupby('fecha', as_index=False)['visitantes'].sum(min_count=1)
         .rename(columns={'visitantes': 'telefonia'}))

    for df in (t, a, m):
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.to_period('M').dt.to_timestamp()
    wide = t.merge(a, on='fecha', how='outer').merge(m, on='fecha', how='outer').sort_values('fecha')
    wide = wide.dropna(subset=list(FUENTES), how='all')
    return completar_calendario(wide, freq='MS')


def cobertura_fuentes(wide: pd.DataFrame) -> pd.DataFrame:
    """Primer y último mes con dato, meses con dato y huecos dentro de ese rango."""
    filas = []
    for col, nombre in FUENTES.items():
        if col not in wide.columns:
            continue
        s = wide.loc[wide[col].notna(), 'fecha']
        if s.empty:
            filas.append(dict(fuente=nombre, primer_mes=None, ultimo_mes=None, meses_con_dato=0,
                              meses_sin_dato_en_rango=0))
            continue
        rango = pd.date_range(s.min(), s.max(), freq='MS')
        filas.append(dict(fuente=nombre, primer_mes=s.min(), ultimo_mes=s.max(),
                          meses_con_dato=int(s.nunique()),
                          meses_sin_dato_en_rango=int(len(rango.difference(pd.DatetimeIndex(s))))))
    return pd.DataFrame(filas)


def variacion_mensual_pct(serie: pd.Series) -> pd.Series:
    """Variación % entre meses calendario ADYACENTES con dato.

    Requiere calendario completo (una fila por mes); si falta alguno de los dos meses, NaN.
    """
    actual = pd.to_numeric(serie, errors='coerce')
    previo = actual.shift(1)
    return ((actual / previo - 1) * 100).where(actual.notna() & previo.gt(0))


def concordancia_pares(wide: pd.DataFrame, minimo_meses: int = 4) -> pd.DataFrame:
    """Concordancia descriptiva entre cada par de fuentes, solo en meses comunes.

    - ``meses_comunes``: meses con dato en ambas fuentes.
    - ``correlacion_niveles``: Pearson de los niveles (NaN si hay menos de ``minimo_meses``).
      Con estacionalidad compartida y pocos meses es indicativa, no concluyente.
    - ``misma_direccion_pct``: % de variaciones mensuales comparables en que ambas fuentes
      suben o bajan a la vez (variaciones solo entre meses adyacentes con dato en ambas).
    """
    d = completar_calendario(wide, freq='MS').sort_values('fecha').reset_index(drop=True)
    cols = [c for c in FUENTES if c in d.columns]
    var = {c: variacion_mensual_pct(d[c]) for c in cols}
    filas = []
    for a, b in combinations(cols, 2):
        comun = d[['fecha', a, b]].dropna()
        n = len(comun)
        r = comun[a].corr(comun[b]) if n >= minimo_meses else np.nan
        ok = var[a].notna() & var[b].notna()
        nv = int(ok.sum())
        misma = float((np.sign(var[a][ok]) == np.sign(var[b][ok])).mean() * 100) if nv else np.nan
        filas.append(dict(par=f'{FUENTES[a]} vs {FUENTES[b]}', meses_comunes=n,
                          primer_mes=comun['fecha'].min() if n else pd.NaT,
                          ultimo_mes=comun['fecha'].max() if n else pd.NaT,
                          correlacion_niveles=r, variaciones_comparables=nv,
                          misma_direccion_pct=misma))
    return pd.DataFrame(filas)


def indice_base_100(wide: pd.DataFrame, columnas=None):
    """Índices base 100 en el primer mes donde TODAS las columnas tienen dato.

    Devuelve (DataFrame con fecha y una columna por fuente, mes_base) o (None, None)
    si no existe un mes común. Las fuentes siguen en su propia unidad: es variación relativa.
    """
    cols = [c for c in (columnas or FUENTES) if c in wide.columns]
    if not cols:
        return None, None
    comunes = wide.loc[wide[cols].notna().all(axis=1) & wide[cols].gt(0).all(axis=1), 'fecha']
    if comunes.empty:
        return None, None
    base = comunes.min()
    ref = wide.loc[wide['fecha'].eq(base), cols].iloc[0]
    out = wide[['fecha']].copy()
    for c in cols:
        out[c] = wide[c] / ref[c] * 100
    return out, base
