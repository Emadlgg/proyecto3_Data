"""Registro local de runs del Laboratorio 11 con MLflow Tracking.

Usar un directorio local o volumen Docker para evitar publicar microdatos.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path


def registrar_ejecucion(record: dict, config: dict, run_dir: Path, tracking_uri: str,
                        experiment: str = 'Observatorio_Tikal_Flores_Peten') -> str:
    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError('Falta mlflow: pip install mlflow') from exc
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=record['run_id']) as run:
        mlflow.set_tags({'git_commit': record.get('git_commit','desconocido'),
                         'estado': record.get('estado','desconocido'),
                         'destino': 'Tikal y Flores, Peten',
                         'pipeline_run_id': record['run_id']})
        mlflow.log_params({'config_sha256':record.get('config_sha256',''),
                           'calibracion_anio': config['calibracion']['anio'],
                           'calibracion_meses': ','.join(map(str,config['calibracion']['meses'])),
                           'ratio_mae_maximo':config['evaluacion']['ratio_mae_maximo'],
                           'nmae_maximo':config['evaluacion']['nmae_maximo']})
        for nombre, valor in record.get('decision', {}).items():
            if nombre in ('MAE_modelo','MAE_referencia','ratio_mae','nMAE') and isinstance(valor,(int,float)):
                mlflow.log_metric(nombre, float(valor))
        for nombre, huella in record.get('fuentes',{}).items():
            mlflow.set_tag('fuente_sha256_' + str(len(nombre)) + '_' + hashlib.sha256(nombre.encode()).hexdigest()[:10], huella)
        # Huellas completas en artefacto, sin exponer archivos institucionales.
        manifest = run_dir / 'trazabilidad.json'
        manifest.write_text(json.dumps({'fuentes':record.get('fuentes',{}),
                                        'git_commit':record.get('git_commit'),
                                        'controles':record.get('controles_criticos'),
                                        'decision':record.get('decision'),
                                        'config':config},indent=2,ensure_ascii=False),encoding='utf-8')
        for filename in ('ejecucion.json','calidad.json','trazabilidad.json','evaluacion_temporal.csv','metricas_temporales.csv'):
            p = run_dir / filename
            if p.exists():
                mlflow.log_artifact(str(p), artifact_path='evidencia')
        pred = run_dir / 'processed' / 'predicciones' / 'prediccion_peten_ene_feb_2026.csv'
        if pred.exists():
            mlflow.log_artifact(str(pred), artifact_path='estimaciones')
        return run.info.run_id
