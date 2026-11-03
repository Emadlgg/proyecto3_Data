import json
import pandas as pd
import pytest
from src.publicacion import publicar, consultar, restaurar, digest, FILE


def record(run, accepted=True, demo=False, file=None):
    r = {'run_id': run, 'estado': 'CANDIDATO_ACEPTADO_NO_PUBLICADO' if accepted else 'CANDIDATO_RECHAZADO_NO_PUBLICADO', 'decision': {'aprobado': accepted}, 'demo_sintetica': demo}
    if file and not demo:
        r['salidas'] = {'processed/predicciones/' + FILE: digest(file)}
    return r


def sample(tmp_path, value=10):
    path = tmp_path / FILE
    pd.DataFrame({'fecha':['2026-01-01','2026-02-01'],'subdestino':['Flores']*2,'segmento':['mayor a 1 dia']*2,'visitantes_estimados':[value,value+1]}).to_csv(path,index=False)
    return path


def test_rechazado_no_publica(tmp_path):
    file = sample(tmp_path)
    with pytest.raises(PermissionError):
        publicar(record('bad', False), file, tmp_path)
    assert consultar(tmp_path) is None


def test_publicacion_y_restauracion(tmp_path):
    file = sample(tmp_path)
    publicar(record('v1', file=file), file, tmp_path)
    file = sample(tmp_path, 20)
    publicar(record('v2', file=file), file, tmp_path)
    assert consultar(tmp_path)[1]['run_id'] == 'v2'
    restaurar(tmp_path, 'v1')
    assert consultar(tmp_path)[1]['run_id'] == 'v1'


def test_hash_distinto_bloqueado(tmp_path):
    file = sample(tmp_path)
    r = record('v1', file=file)
    file = sample(tmp_path, 100)
    with pytest.raises(ValueError):
        publicar(r, file, tmp_path)


def test_demo_no_se_publica_como_real(tmp_path):
    file = sample(tmp_path)
    with pytest.raises(PermissionError):
        publicar(record('demo', demo=True), file, tmp_path)


def test_version_corrupta_no_se_consulta(tmp_path):
    file = sample(tmp_path)
    publicar(record('v1', file=file), file, tmp_path)
    (tmp_path/'approved'/'versions'/'v1'/FILE).write_text('corrupto')
    with pytest.raises(ValueError):
        consultar(tmp_path)
