"""Pipeline inicial del Laboratorio 11: ETL, calidad, indicadores y predicciones.



Ejecutar: python -m src.pipeline --config config/mlops.json

Solo publica candidatos aprobados si la configuracion habilita la publicacion automatica.

"""

from __future__ import annotations

import argparse

import hashlib

import json

import logging

import os
import re


import subprocess

import sys


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
    """Usa el SHA proporcionado por Compose; si falta, consulta Git local."""
    env_commit = os.environ.get('GIT_COMMIT', '').strip()
    if env_commit and env_commit.lower() not in {'desconocido', 'sin_commit_disponible'}:
        if not re.fullmatch(r'[0-9a-fA-F]{40}', env_commit):
            raise ValueError('GIT_COMMIT debe ser un SHA Git completo de 40 caracteres hexadecimales')
        return env_commit.lower()
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
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

        dates = pd.to_datetime(df['fecha'], errors='coerce', format='%Y-%m-%d')

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

    from src.evaluacion import evaluar_temporal, decidir_aceptacion

    from src.mlflow_tracking import registrar_ejecucion

    from src.monitoreo import evaluar as evaluar_monitoreo

    from src.publicacion import publicar

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

        mov = pd.read_csv(stage / 'movilidad_mensual_peten.csv', parse_dates=['fecha'])

        mig = pd.read_csv(stage / 'migracion_nacional_mensual.csv', parse_dates=['fecha'])

        perfil = pd.read_csv(stage / 'predicciones' / 'perfil_estacional_nacional.csv')

        detalle, resumen = evaluar_temporal(mov, mig, perfil,

            meses=cfg['evaluacion']['meses'], anio=cfg['calibracion']['anio'])

        detalle.to_csv(run / 'evaluacion_temporal.csv', index=False)

        resumen.to_csv(run / 'metricas_temporales.csv', index=False)

        record['decision'] = decidir_aceptacion(detalle, cfg, calidad_ok=True, salidas_ok=True)

        record['etapas'].append('evaluacion_temporal')

        record['salidas'] = {str(p.relative_to(run)):sha256(p) for p in stage.rglob('*.csv')}

        record['monitoreo'] = evaluar_monitoreo(stage, cfg)

        (run / 'monitoreo.json').write_text(json.dumps(record['monitoreo'], ensure_ascii=False, indent=2), encoding='utf-8')

        record['etapas'].append('monitoreo')

        # Las alertas de revision no modifican retroactivamente los umbrales predictivos.

        criticas = [a for a in record['monitoreo']['alertas'] if a.startswith('CRITICO:')]

        if criticas:

            raise ValueError('Monitoreo critico: ' + '; '.join(criticas))

        record['estado'] = 'CANDIDATO_ACEPTADO_NO_PUBLICADO' if record['decision']['aprobado'] else 'CANDIDATO_RECHAZADO_NO_PUBLICADO'

    except Exception as exc:

        record['estado'] = 'FALLIDO_NO_PUBLICADO'

        record['errores'].append(f'{type(exc).__name__}: {exc}')

        LOG.exception('Pipeline detenido; no se publicó ningún archivo')

    finally:

        record['fin_utc'] = datetime.now(timezone.utc).isoformat()

        (run / 'ejecucion.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

        try:

            mlflow_id = registrar_ejecucion(record, cfg, run,

                os.environ.get('MLFLOW_TRACKING_URI', cfg['mlflow']['tracking_uri']), cfg['mlflow']['experimento'])

            record['mlflow_run_id'] = mlflow_id

        except Exception as ml_exc:

            record['errores'].append(f'MLflow: {type(ml_exc).__name__}: {ml_exc}')

            record['estado'] = 'FALLIDO_TRACKING_NO_PUBLICADO'

        # Publicar solo si la evaluacion, la calidad y el registro MLflow fueron exitosos.

        # El estado rechazado es valido y nunca sustituye la version anterior.

        if not record['errores'] and record['estado'] == 'CANDIDATO_ACEPTADO_NO_PUBLICADO' and cfg.get('publicacion', {}).get('automatica', False):

            try:

                archivo = stage / 'predicciones' / 'prediccion_peten_ene_feb_2026.csv'

                meta = publicar(record, archivo, (ROOT / cfg['rutas'].get('artefactos', 'artifacts')).resolve())

                record['publicado'] = True

                record['estado'] = 'APROBADO_PUBLICADO'

                record['version_publicada'] = meta['run_id']

                record['etapas'].append('publicacion')

            except Exception as pub_exc:

                record['errores'].append(f'Publicacion: {type(pub_exc).__name__}: {pub_exc}')

                record['estado'] = 'FALLIDO_PUBLICACION_NO_PUBLICADO'

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
