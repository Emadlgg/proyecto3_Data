"""Monitoreo de calidad, vigencia y resultados sin modificar datos.

Uso: python -m src.monitoreo --data data/processed --config config/mlops.json
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd


def evaluar(data: Path, config: dict) -> dict:
    alerts = []
    checks = {}
    paths = {
        'movilidad': data / 'movilidad_mensual_peten.csv',
        'migracion': data / 'migracion_nacional_mensual.csv',
        'predicciones': data / 'predicciones' / 'prediccion_peten_ene_feb_2026.csv',
    }
    for name, path in paths.items():
        if not path.exists():
            alerts.append(f'CRITICO: falta {name}: {path}')
            continue
        df = pd.read_csv(path)
        if df.empty:
            alerts.append(f'CRITICO: {name} vacio')
            continue
        checks[name] = {'filas': int(len(df)), 'nulos': int(df.isna().sum().sum()), 'duplicados_exactos': int(df.duplicated().sum())}
        if df.duplicated().any():
            alerts.append(f'CALIDAD: duplicados en {name}')
        if 'fecha' in df.columns:
            dates = pd.to_datetime(df['fecha'], format='%Y-%m-%d', errors='coerce')
            if dates.isna().any():
                alerts.append(f'CRITICO: fechas invalidas en {name}')
            else:
                checks[name]['ultima_fecha'] = str(dates.max().date())
                if name == 'movilidad':
                    required = set(config.get('monitoreo', {}).get('meses_movilidad_esperados', ['2025-09','2025-10','2025-11','2025-12','2026-03','2026-04','2026-05','2026-06','2026-07','2026-08']))
                    observed = set(dates.dt.strftime('%Y-%m'))
                    if required - observed:
                        alerts.append('ACTUALIZACION: movilidad sin meses esperados: ' + ', '.join(sorted(required - observed)))
                if name == 'predicciones' and set(dates.dt.strftime('%Y-%m')) != {'2026-01','2026-02'}:
                    alerts.append('ACTUALIZACION: predicciones no cubren exactamente enero-febrero 2026')
        if name == 'predicciones' and 'visitantes_estimados' in df:
            vals = pd.to_numeric(df['visitantes_estimados'], errors='coerce')
            if vals.isna().any() or not np.isfinite(vals).all() or (vals < 0).any():
                alerts.append('CRITICO: estimaciones negativas/no finitas')
            threshold = float(config.get('monitoreo', {}).get('variacion_mensual_alerta', 0.75))
            for _, group in df.assign(_fecha=pd.to_datetime(df['fecha'], errors='coerce')).groupby(['subdestino','segmento']):
                group = group.sort_values('_fecha')
                values = pd.to_numeric(group['visitantes_estimados'], errors='coerce')
                if len(values) > 1 and values.iloc[0] > 0:
                    change = abs(values.iloc[1] / values.iloc[0] - 1)
                    if np.isfinite(change) and change > threshold:
                        alerts.append(f'REVISION: variacion mensual {change:.1%} supera umbral {threshold:.0%}')
    return {'fecha_utc': datetime.now(timezone.utc).isoformat(), 'controles': checks, 'alertas': alerts,
            'nota': 'Variaciones elevadas son alertas, no pruebas de perdida de precision.'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path('data/processed'))
    parser.add_argument('--config', type=Path, default=Path('config/mlops.json'))
    parser.add_argument('--out', type=Path, default=Path('artifacts/monitoreo/ultimo.json'))
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    result = evaluar(args.data, cfg)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Alertas:', len(result['alertas']))
    for msg in result['alertas']:
        print(msg)
    print('Reporte:', args.out)

if __name__ == '__main__':
    main()
