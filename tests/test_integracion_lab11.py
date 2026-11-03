"""Pruebas de integracion de la publicacion controlada sin datos institucionales."""
from pathlib import Path
import pandas as pd
import pytest
from src.publicacion import FILE, consultar, publicar, digest


def candidato(tmp_path: Path, run_id: str, aprobado: bool, valor: float):
    archivo = tmp_path / f'{run_id}.csv'
    pd.DataFrame([
        {'fecha': '2026-01-01', 'subdestino': 'Prueba', 'segmento': 'mayor a 1 dia', 'visitantes_estimados': valor},
        {'fecha': '2026-02-01', 'subdestino': 'Prueba', 'segmento': 'mayor a 1 dia', 'visitantes_estimados': valor + 2},
    ]).to_csv(archivo, index=False)
    return archivo, {
        'run_id': run_id,
        'estado': 'CANDIDATO_ACEPTADO_NO_PUBLICADO' if aprobado else 'CANDIDATO_RECHAZADO_NO_PUBLICADO',
        'decision': {'aprobado': aprobado, 'MAE_modelo': 1.0},
        'salidas': {f'processed/predicciones/{FILE}': digest(archivo)},
    }


def test_rechazo_no_crea_version(tmp_path):
    archivo, record = candidato(tmp_path, 'r1', False, 10)
    with pytest.raises(PermissionError):
        publicar(record, archivo, tmp_path)
    assert consultar(tmp_path) is None


def test_fallo_no_sustituye_version_previa(tmp_path):
    archivo, record = candidato(tmp_path, 'r1', True, 10)
    publicar(record, archivo, tmp_path)
    previo = consultar(tmp_path)[1]['sha256']
    archivo2, record2 = candidato(tmp_path, 'r2', False, 20)
    with pytest.raises(PermissionError):
        publicar(record2, archivo2, tmp_path)
    assert consultar(tmp_path)[1]['sha256'] == previo


def test_version_corrupta_no_se_muestra(tmp_path):
    archivo, record = candidato(tmp_path, 'r1', True, 10)
    publicar(record, archivo, tmp_path)
    ruta, _ = consultar(tmp_path)
    ruta.write_text('archivo alterado', encoding='utf-8')
    with pytest.raises(ValueError):
        consultar(tmp_path)
