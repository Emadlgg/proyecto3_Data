"""Imputación de enero–febrero 2026 (meses sin cobertura de telefonía) para Petén.

Idea: los visitantes de un polígono/segmento se modelan como
    visitantes(t) = factor_reparto(t) × viajeros_nacionales(t)
con migración nacional de Base_Migracion (perfil estacional y/o observada) y un factor de
reparto observado del destino. Como la telefonía SÍ existe antes (sep–dic 2025) y después
(mar–ago 2026) del hueco, el factor se interpola entre ambos lados (imputación acotada),
en lugar de proyectarlo hacia adelante.

Validación: se repite el mismo problema (ocultar 2 meses consecutivos con vecinos observados
a ambos lados) sobre meses que sí tienen dato, y se reportan MAE, RMSE y MAPE por método.

Reglas del curso respetadas: no se suman polígonos; lo imputado se rotula 'Estimación';
los meses sin cobertura no se rellenan con cero.

Uso: python -m src.imputacion
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.predicciones import cargar, perfil_historico, PROCESSED, OUT

OBJETIVO = ['2026-01-01', '2026-02-01']
PRINCIPAL = 'interpolado_observada'
# Métodos que combinan migración × factor de reparto (la metodología pedida en la guía).
METODOS_GUIA = ['interpolado_observada', 'interpolado_perfil', 'ultimo_observada', 'mediano_observada']
METODOS_REFERENCIA = ['persistencia', 'interp_lineal_nivel']
ETIQUETAS = {
    'interpolado_observada': 'Factor interpolado × migración observada',
    'interpolado_perfil': 'Factor interpolado × migración por perfil estacional',
    'ultimo_observada': 'Último factor × migración observada',
    'mediano_observada': 'Factor mediano × migración observada',
    'persistencia': 'Referencia: último valor observado',
    'interp_lineal_nivel': 'Referencia: interpolación lineal de visitantes',
}


def _t(fecha) -> int:
    f = pd.Timestamp(fecha)
    return f.year * 12 + f.month - 1


def _nacional_perfil(nat: pd.Series, perfil: pd.DataFrame, ancla: list[pd.Timestamp],
                     objetivo: list[pd.Timestamp]) -> dict[pd.Timestamp, float]:
    """Nivel anclado en los meses vecinos observados × índice estacional del mes objetivo."""
    idx = perfil.set_index('mes').indice
    niveles = [nat[a] / idx[a.month] for a in ancla]
    nivel = float(np.median(niveles))
    return {o: nivel * float(idx[o.month]) for o in objetivo}


def estimar_hueco(g: pd.DataFrame, nat: pd.Series, perfil: pd.DataFrame,
                  objetivo: list[pd.Timestamp]) -> dict[str, list[float]]:
    """Estimaciones de todos los métodos para un hueco, SIN mirar los valores del objetivo.

    g: serie observada del grupo (fecha, visitantes) que ya excluye los meses objetivo.
    nat: migración nacional observada indexada por fecha (se usa en objetivo solo en
         los métodos que declaran 'observada').
    """
    antes = objetivo[0] - pd.offsets.MonthBegin(1)
    despues = objetivo[-1] + pd.offsets.MonthBegin(1)
    s = g.set_index('fecha').visitantes
    if antes not in s.index or despues not in s.index:
        raise ValueError('El hueco debe tener meses observados a ambos lados')
    ratio = s / nat.reindex(s.index)
    ratio = ratio.dropna()
    r0, r1, t0, t1 = ratio[antes], ratio[despues], _t(antes), _t(despues)
    perfil_nat = _nacional_perfil(nat, perfil, [antes, despues], objetivo)
    res: dict[str, list[float]] = {k: [] for k in METODOS_GUIA + METODOS_REFERENCIA}
    mediano = float(np.median(ratio.values))
    for o in objetivo:
        w = (_t(o) - t0) / (t1 - t0)
        r_int = r0 + w * (r1 - r0)
        res['interpolado_observada'].append(float(r_int * nat[o]))
        res['interpolado_perfil'].append(float(r_int * perfil_nat[o]))
        res['ultimo_observada'].append(float(r0 * nat[o]))
        res['mediano_observada'].append(float(mediano * nat[o]))
        res['persistencia'].append(float(s[antes]))
        res['interp_lineal_nivel'].append(float(s[antes] + w * (s[despues] - s[antes])))
    return res


def _ventanas(g: pd.DataFrame, nat: pd.Series) -> list[list[pd.Timestamp]]:
    """Pares de meses consecutivos observados con vecino observado a cada lado y migración disponible."""
    obs = set(g.fecha)
    out = []
    for m in sorted(obs):
        m2 = m + pd.offsets.MonthBegin(1)
        a, d = m - pd.offsets.MonthBegin(1), m2 + pd.offsets.MonthBegin(1)
        if {m2, a, d} <= obs and all(x in nat.index for x in (a, m, m2, d)):
            out.append([m, m2])
    return out


def backtest(mov: pd.DataFrame, mig: pd.DataFrame, perfil: pd.DataFrame) -> pd.DataFrame:
    nat = mig.set_index('fecha').viajeros_nacionales
    filas = []
    for (sub, seg), g in mov.groupby(['subdestino', 'segmento']):
        g = g.sort_values('fecha')
        for obj in _ventanas(g, nat):
            oculto = g[~g.fecha.isin(obj)]
            est = estimar_hueco(oculto, nat, perfil, obj)
            real = g.set_index('fecha').visitantes
            for metodo, vals in est.items():
                for o, e in zip(obj, vals):
                    filas.append({'subdestino': sub, 'segmento': seg, 'ventana': f'{obj[0]:%Y-%m}/{obj[1]:%Y-%m}',
                                  'fecha': o, 'metodo': metodo, 'observado': float(real[o]),
                                  'estimado': e, 'error': e - float(real[o])})
    if not filas:
        raise ValueError('No hay ventanas válidas para validar la imputación')
    d = pd.DataFrame(filas)
    d['error_pct_abs'] = np.where(d.observado > 0, 100 * d.error.abs() / d.observado, np.nan)
    return d


def resumen_backtest(detalle: pd.DataFrame) -> pd.DataFrame:
    r = (detalle.groupby('metodo', as_index=False)
         .agg(n=('error', 'size'), ventanas=('ventana', 'nunique'),
              MAE=('error', lambda x: float(np.mean(np.abs(x)))),
              RMSE=('error', lambda x: float(np.sqrt(np.mean(np.square(x))))),
              MAPE=('error_pct_abs', 'mean'), sesgo_medio=('error', 'mean')))
    r['etiqueta'] = r.metodo.map(ETIQUETAS)
    r['tipo'] = np.where(r.metodo.isin(METODOS_GUIA), 'Migración × reparto (guía)', 'Referencia')
    return r.sort_values('MAE').reset_index(drop=True)


def imputar(mov: pd.DataFrame, mig: pd.DataFrame, perfil: pd.DataFrame) -> pd.DataFrame:
    nat = mig.set_index('fecha').viajeros_nacionales
    objetivo = [pd.Timestamp(x) for x in OBJETIVO]
    faltan = [o for o in objetivo if o not in nat.index]
    if faltan:
        raise ValueError(f'Falta migración nacional observada en {faltan}')
    filas = []
    for (sub, seg), g in mov.groupby(['subdestino', 'segmento']):
        g = g.sort_values('fecha')
        if g.fecha.isin(objetivo).any():
            raise ValueError('Los meses objetivo ya tienen telefonía; no se imputan')
        est = estimar_hueco(g, nat, perfil, objetivo)
        for metodo, vals in est.items():
            for o, e in zip(objetivo, vals):
                filas.append({'fecha': o, 'subdestino': sub, 'segmento': seg, 'metodo': metodo,
                              'etiqueta': ETIQUETAS[metodo], 'visitantes_estimados': e,
                              'principal': metodo == PRINCIPAL, 'tipo_dato': 'Estimación',
                              'migracion_observada_usada': float(nat[o])})
    return pd.DataFrame(filas).sort_values(['subdestino', 'segmento', 'metodo', 'fecha']).reset_index(drop=True)


def validar_perfil_nacional(mig: pd.DataFrame, perfil: pd.DataFrame) -> pd.DataFrame:
    """Compara la migración nacional estimada solo con perfil (anclaje sep–dic 2025) contra lo observado."""
    from src.predicciones import estimar_nacional
    est = estimar_nacional(mig, perfil, [1, 2])
    obs = mig[mig.fecha.isin(est.fecha)][['fecha', 'viajeros_nacionales']]
    d = est.merge(obs, on='fecha')
    d['error'] = d.migracion_nacional_estimada - d.viajeros_nacionales
    d['error_pct'] = 100 * d.error / d.viajeros_nacionales
    return d


def ejecutar(directorio: Path = PROCESSED, salida: Path = OUT) -> dict[str, pd.DataFrame]:
    mov, mig = cargar(directorio)
    perfil = perfil_historico(mig)
    mov = mov[mov.fecha.isin(mig.fecha)].copy()  # solo meses con migración nacional para razón de reparto
    det = backtest(mov, mig, perfil)
    res = resumen_backtest(det)
    imp = imputar(mov, mig, perfil)
    perf = validar_perfil_nacional(mig, perfil)
    salidas = {'imputacion_ene_feb_2026.csv': imp,
               'backtest_imputacion_detalle.csv': det,
               'backtest_imputacion_resumen.csv': res,
               'validacion_perfil_nacional_ene_feb_2026.csv': perf}
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, df in salidas.items():
        df.to_csv(salida / nombre, index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
        print(f'{nombre}: {len(df)} filas')
    return salidas


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--processed', type=Path, default=PROCESSED)
    p.add_argument('--out', type=Path, default=OUT)
    a = p.parse_args()
    ejecutar(a.processed, a.out)


if __name__ == '__main__':
    main()
