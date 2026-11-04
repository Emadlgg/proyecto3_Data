"""Candidato exploratorio de persistencia para dos meses sin observaciones.

No modifica predicciones.py, pipeline.py ni publica resultados.
Ejecutar: python -m src.predicciones_candidatas --data data/processed
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
GROUP = ['subdestino', 'segmento']


def estimar_persistencia(movilidad: pd.DataFrame, corte='2025-12-01', objetivos=('2026-01-01', '2026-02-01')) -> pd.DataFrame:
    required = set(GROUP + ['fecha', 'visitantes'])
    if not required.issubset(movilidad.columns):
        raise ValueError(f'Columnas faltantes: {sorted(required - set(movilidad.columns))}')
    df = movilidad.copy()
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df['visitantes'] = pd.to_numeric(df['visitantes'], errors='coerce')
    if df['fecha'].isna().any() or not np.isfinite(df['visitantes']).all() or (df['visitantes'] < 0).any():
        raise ValueError('Fechas o visitantes invalidos')
    if df.duplicated(GROUP + ['fecha']).any():
        raise ValueError('Claves duplicadas')
    corte = pd.Timestamp(corte)
    targets = [pd.Timestamp(x) for x in objetivos]
    if len(targets) != 2 or targets != [corte + pd.DateOffset(months=i) for i in (1, 2)]:
        raise ValueError('Se requieren exactamente dos meses consecutivos posteriores al corte')
    historico = df[df['fecha'] <= corte]
    if historico.empty:
        raise ValueError('No hay historial hasta el corte')
    ultimo = historico.sort_values('fecha').groupby(GROUP, as_index=False).tail(1)
    if not ultimo['fecha'].eq(corte).all():
        raise ValueError('Cada grupo debe tener un dato observado en el mes de corte')
    rows = []
    for _, r in ultimo.iterrows():
        for fecha in targets:
            rows.append({'fecha': fecha, 'subdestino': r['subdestino'], 'segmento': r['segmento'],
                         'visitantes_estimados': float(r['visitantes']), 'metodo': 'persistencia',
                         'fecha_corte': corte, 'fecha_base': r['fecha'], 'tipo_dato': 'estimacion_exploratoria'})
    return pd.DataFrame(rows).sort_values(GROUP + ['fecha']).reset_index(drop=True)


def ejecutar(data: Path, out: Path | None = None) -> Path:
    data = Path(data)
    out = Path(out) if out is not None else data / 'optimizacion'
    df = pd.read_csv(data / 'movilidad_mensual_peten.csv')
    result = estimar_persistencia(df)
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'candidata_persistencia_ene_feb_2026.csv'
    result.to_csv(target, index=False)
    print(f'{target}: {len(result)} filas; NO PUBLICADO')
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=BASE / 'data' / 'processed')
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    ejecutar(a.data, a.out)

if __name__ == '__main__':
    main()
