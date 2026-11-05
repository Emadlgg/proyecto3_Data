"""Pruebas de los cálculos compartidos por la página de encuestas."""
import pandas as pd
from src.ui.analitica import filtrar_encuesta, resumen_encuesta, resumen_satisfaccion


def test_filtrado_por_lugar_y_tipo():
    df = pd.DataFrame({'Lugar_Turistico':['Flores','Tikal'], 'tipo_visitante':['A','B'], 'indicador':['edad','edad']})
    out = filtrar_encuesta(df, ['Flores'], ['A'])
    assert len(out) == 1 and out.iloc[0]['Lugar_Turistico'] == 'Flores'


def test_porcentajes_se_recalculan_desde_recuentos():
    df = pd.DataFrame({'indicador':['edad']*3, 'respuesta':['20-29','20-29','30-39'],
                       'n_respuestas':[2,3,5]})
    r = resumen_encuesta(df, 'edad')
    assert r.base_valida.eq(10).all()
    assert abs(r.porcentaje_muestra.sum() - 100) < 1e-9
    assert r.loc[r.respuesta.eq('20-29'), 'n_respuestas'].iloc[0] == 5


def test_satisfaccion_ponderada_por_respuestas():
    df = pd.DataFrame({'variable':['q','q'], 'n_respuestas':[1,9],
                       'media_muestra':[1,5], 'porcentaje_4_5':[0,100]})
    r = resumen_satisfaccion(df, 'q')
    assert r['n'] == 10
    assert abs(r['media'] - 4.6) < 1e-9
    assert abs(r['porcentaje_4_5'] - 90) < 1e-9
