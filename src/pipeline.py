"""Pipeline inicial del Laboratorio 11: ETL, calidad, indicadores y predicciones.

Ejecutar: python -m src.pipeline --config config/mlops.json
No publica resultados ni sobrescribe los CSV aprobados. Guarda candidatos aislados.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'sin_commit_disponible'


def control_critico(df: pd.DataFrame, required: tuple[str, ...], key: tuple[str, ...], numeric: tuple[str, ...], name: str) -> None:
    """Seis reglas: esquema/tipos, fechas/cobertura, clave, faltantes, valores y metodología."""
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f'{name}: columnas ausentes: {sorted(missing)}')
    if df.empty:
        raise ValueError(f'{name}: sin registros')
    if df.duplicated(list(key)).any():
        raise ValueError(f'{name}: clave duplicada: {key}')
    if 'fecha' in required:
        dates = pd.to_datetime(df['fecha'], errors='coerce')
        if dates.isna().any():
            raise ValueError(f'{name}: fechas inválidas')
    for col in numeric:
        vals = pd.to_numeric(df[col], errors='coerce')
        if vals.isna().any():
            raise ValueError(f'{name}: {col} vacío o no numérico')
        if (~pd.Series(__import__('numpy').isfinite(vals.to_numpy()))).any() or (vals < 0).any():
            raise ValueError(f'{name}: {col} negativo/no finito')


def controles_calibracion(staging: Path, cfg: dict) -> dict:
    mov = pd.read_csv(staging / 'movilidad_mensual_peten.csv', parse_dates=['fecha'])
    mig = pd.read_csv(staging / 'migracion_nacional_mensual.csv', parse_dates=['fecha'])
    control_critico(mov, ('fecha','subdestino','segmento','visitantes','dias_persona'),
                    ('fecha','subdestino','segmento'), ('visitantes','dias_persona'), 'movilidad')
    control_critico(mig, ('fecha','viajeros_nacionales'), ('fecha',), ('viajeros_nacionales',), 'migracion')
    months = set(cfg['calibracion']['meses'])
    year = int(cfg['calibracion']['anio'])
    observed = mov[(mov.fecha.dt.year == year) & mov.fecha.dt.month.isin(months)]
    if observed.empty:
        raise ValueError('No existen meses de calibración')
    for group, df in observed.groupby(['subdestino','segmento']):
        if set(df.fecha.dt.month) != months:
            raise ValueError(f'Cobertura incompleta de calibración para {group}')
    nat = mig[(mig.fecha.dt.year == year) & mig.fecha.dt.month.isin(months)]
    if set(nat.fecha.dt.month) != months or (nat.viajeros_nacionales <= 0).any():
        raise ValueError('Migración nacional sin cobertura o denominador cero en calibración')
    if ((mov.fecha.dt.year == 2026) & mov.fecha.dt.month.isin([1,2])).any():
        raise ValueError('Meses sin cobertura telefónica se registraron como observados')
    if (mov.dias_persona < mov.visitantes).any():
        raise ValueError('Días-persona menores que visitantes')
    return {'controles': ['columnas_y_tipos','fechas_y_cobertura','unicidad',
                         'faltantes_criticos','valores_y_denominadores','regla_metodologica'],
            'calibracion': f'{year}: {sorted(months)}',
            'regla': 'fuente mensual, no suma de presencias diarias; subdestinos separados'}


def ejecutar(config_path: Path) -> dict:
    from src import etl, indicadores, predicciones, validaciones
    config_path = config_path.resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    raw = (ROOT / cfg['rutas']['raw']).resolve()
    base = (ROOT / cfg['rutas']['candidatos']).resolve()
    if not raw.is_dir():
        raise FileNotFoundError(f'Falta carpeta privada de datos: {raw}')
    started = datetime.now(timezone.utc)
    run_id = started.strftime('%Y%m%dT%H%M%S%fZ')
    run = base / run_id
    stage = run / 'processed'
    stage.mkdir(parents=True, exist_ok=False)
    record = {'run_id':run_id, 'inicio_utc':started.isoformat(), 'git_commit':git_commit(),
              'config_sha256':sha256(config_path), 'estado':'INICIADO', 'etapas':[],
              'advertencias':[], 'errores':[], 'publicado':False}
    try:
        record['fuentes'] = {p.name:sha256(p) for p in sorted(raw.iterdir()) if p.is_file()}
        etl.ejecutar(raw, stage)
        record['etapas'].append('etl')
        report = validaciones.evaluar(stage)
        (run / 'calidad.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        record['advertencias'].extend(report['advertencias'])
        if report['errores']:
            raise ValueError('Controles de calidad: ' + '; '.join(report['errores']))
        record['controles_criticos'] = controles_calibracion(stage, cfg)
        record['etapas'].append('calidad')
        indicadores.ejecutar(stage, stage / 'indicadores')
        record['etapas'].append('indicadores')
        predicciones.ejecutar(stage, stage / 'predicciones')
        record['etapas'].append('predicciones')
        pred = pd.read_csv(stage / 'predicciones' / 'prediccion_peten_ene_feb_2026.csv')
        if pred.empty or pred['visitantes_estimados'].isna().any() or (pred['visitantes_estimados'] < 0).any():
            raise ValueError('Estimaciones inválidas')
        expected = set(cfg['objetivo']['meses'])
        if set(pd.to_datetime(pred['fecha']).dt.month) != expected:
            raise ValueError('Meses objetivo incompletos')
        record['etapas'].append('verificacion_salidas')
        record['salidas'] = {str(p.relative_to(run)):sha256(p) for p in stage.rglob('*.csv')}
        record['estado'] = 'CANDIDATO_VALIDADO_NO_PUBLICADO'
    except Exception as exc:
        record['estado'] = 'FALLIDO_NO_PUBLICADO'
        record['errores'].append(f'{type(exc).__name__}: {exc}')
        LOG.exception('Pipeline detenido; no se publicó ningún archivo')
    finally:
        record['fin_utc'] = datetime.now(timezone.utc).isoformat()
        (run / 'ejecucion.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        LOG.info('Ejecución %s: %s. Reporte: %s', run_id, record['estado'], run / 'ejecucion.json')
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config' / 'mlops.json')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    record = ejecutar(args.config)
    print(f"Estado: {record['estado']} | Run: {record['run_id']}")
    if record['errores']:
        for e in record['errores']:
            print('ERROR:', e)
        sys.exit(1)

if __name__ == '__main__':
    main()
