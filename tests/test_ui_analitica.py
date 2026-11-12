"""Pruebas sin Streamlit para el rediseño analítico."""
import json
import pandas as pd
import pytest
from src.ui.analitica import (serie_poligonos, detalle_mes, filtrar_encuesta,
                              resumen_encuesta, resumen_satisfaccion, version_aprobada,
                              ultimo_candidato)


def test_poligonos_separados():
    d = pd.DataFrame({'fecha': pd.to_datetime(['2025-09-01']*4), 'subdestino':['A','A','B','B'], 'visitantes':[10,20,30,40]})
    out = serie_poligonos(d, ['A','B'])
    assert len(out) == 2
    assert out.set_index('subdestino').visitantes.to_dict() == {'A':30,'B':70}


def test_mes_enlazado():
    d = pd.DataFrame({'fecha':pd.to_datetime(['2025-09-01','2025-10-01']), 'subdestino':['A','A'], 'visitantes':[5,8]})
    assert detalle_mes(d, '2025-10-01', ['A']).visitantes.iloc[0] == 8


def test_perfil_no_promedia_porcentajes():
    d = pd.DataFrame({'indicador':['genero']*3,'respuesta':['F','M','F'], 'n_respuestas':[8,2,1]})
    out = resumen_encuesta(d, 'genero').set_index('respuesta')
    assert out.loc['F','base_valida'] == 11
    assert out.loc['F','porcentaje_muestra'] == pytest.approx(900/11)


def test_satisfaccion_ponderada():
    d = pd.DataFrame({'variable':['T_p20','T_p20'], 'n_respuestas':[1,9], 'media_muestra':[1,5], 'porcentaje_4_5':[0,100]})
    out = resumen_satisfaccion(d,'T_p20')
    assert out['media'] == pytest.approx(4.6)
    assert out['porcentaje_4_5'] == pytest.approx(90)


def test_encuesta_filtra_ambas_dimensiones():
    d = pd.DataFrame({'Lugar_Turistico':['Tikal','Flores'], 'tipo_visitante':['Nacional','Extranjero']})
    assert len(filtrar_encuesta(d,['Tikal'],['Nacional'])) == 1


def test_no_hay_publicacion_sin_aprobacion(tmp_path):
    assert version_aprobada(tmp_path) is None


def _run(root, run_id, **rec):
    carpeta = root / 'runs' / run_id
    carpeta.mkdir(parents=True)
    (carpeta / 'ejecucion.json').write_text(json.dumps({'run_id': run_id, **rec}), encoding='utf-8')


def test_ultimo_candidato_sin_ejecuciones(tmp_path):
    assert ultimo_candidato(tmp_path) is None


def test_ultimo_candidato_toma_el_mas_reciente_y_reporta_rechazo(tmp_path):
    _run(tmp_path, '20261102T000000Z', estado='CANDIDATO_ACEPTADO_NO_PUBLICADO',
         decision={'aprobado': True})
    _run(tmp_path, '20261103T000000Z', estado='CANDIDATO_RECHAZADO_NO_PUBLICADO',
         decision={'aprobado': False, 'MAE_modelo': 9, 'MAE_referencia': 5, 'ratio_mae': 1.8,
                   'umbral_ratio': 1.0, 'razon': 'No cumple umbrales predefinidos'})
    c = ultimo_candidato(tmp_path)
    assert c['run_id'] == '20261103T000000Z' and c['aprobado'] is False
    assert c['ratio_mae'] == 1.8 and c['publicado'] is False


def test_ultimo_candidato_fallido_no_inventa_decision(tmp_path):
    _run(tmp_path, '20261104T000000Z', estado='FALLIDO_NO_PUBLICADO', errores=['ValueError: x'])
    c = ultimo_candidato(tmp_path)
    assert c['aprobado'] is None and c['errores'] == ['ValueError: x']


def test_ultimo_candidato_ignora_json_corrupto(tmp_path):
    carpeta = tmp_path / 'runs' / '20261105T000000Z'
    carpeta.mkdir(parents=True)
    (carpeta / 'ejecucion.json').write_text('{no es json', encoding='utf-8')
    assert ultimo_candidato(tmp_path) is None
