"""Evaluacion temporal aislada de persistencia frente a la referencia vigente.

El candidato de persistencia coincide matematicamente con una referencia de
'ultimo valor observado' cuando ambos usan los mismos cortes y grupos.
No se aprueba ni publica automaticamente ninguna prediccion.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.predicciones_candidatas import estimar_persistencia, GROUP

BASE = Path(__file__).resolve().parents[1]


def evaluar_cortes(movilidad: pd.DataFrame, cortes=('2025-10-01',), exigir_dos_meses=True):
    df = movilidad.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])
    detalles = []
    for corte in cortes:
        cut = pd.Timestamp(corte)
        targets = (cut + pd.DateOffset(months=1), cut + pd.DateOffset(months=2))
        estim = estimar_persistencia(df[df.fecha <= cut], corte=cut, objetivos=targets)
        obs = df[GROUP + ['fecha', 'visitantes']]
        cruce = estim.merge(obs, on=GROUP + ['fecha'], how='left', validate='one_to_one')
        if exigir_dos_meses and cruce['visitantes'].isna().any():
            raise ValueError(f'Corte {cut.date()}: faltan observaciones de evaluacion')
        cruce = cruce.dropna(subset=['visitantes']).copy()
        cruce['error'] = cruce['visitantes_estimados'] - cruce['visitantes']
        cruce['error_absoluto'] = cruce['error'].abs()
        cruce['error_cuadrado'] = cruce['error'] ** 2
        cruce['corte'] = cut
        detalles.append(cruce)
    if not detalles:
        raise ValueError('Sin cortes de evaluacion')
    detalle = pd.concat(detalles, ignore_index=True)
    if detalle.empty:
        raise ValueError('Sin observaciones comparables')
    mae = float(detalle.error_absoluto.mean())
    rmse = float(np.sqrt(detalle.error_cuadrado.mean()))
    # Misma prediccion que la referencia de ultimo valor observado: empate exacto.
    resumen = {'metodo': 'persistencia', 'referencia': 'ultimo_valor_observado',
               'n': int(len(detalle)), 'MAE_modelo': mae, 'RMSE_modelo': rmse,
               'MAE_referencia': mae, 'RMSE_referencia': rmse,
               'ratio_mae': 1.0 if mae > 0 else None,
               'empate_con_referencia': True,
               'aprobacion_automatica': False,
               'nota': 'Empate algebraico con la referencia; no demuestra mejora ni autoriza publicacion.'}
    return detalle, resumen


def ejecutar(data: Path, out: Path | None = None, cortes=('2025-10-01',)):
    data = Path(data)
    out = Path(out) if out is not None else data / 'optimizacion'
    df = pd.read_csv(data / 'movilidad_mensual_peten.csv')
    detalle, resumen = evaluar_cortes(df, cortes)
    out.mkdir(parents=True, exist_ok=True)
    detalle.to_csv(out / 'evaluacion_candidata_persistencia.csv', index=False)
    (out / 'resumen_candidata_persistencia.json').write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    return detalle, resumen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=BASE / 'data' / 'processed')
    p.add_argument('--out', type=Path)
    p.add_argument('--cortes', nargs='+', default=['2025-10-01'])
    a = p.parse_args()
    ejecutar(a.data, a.out, a.cortes)

if __name__ == '__main__':
    main()
