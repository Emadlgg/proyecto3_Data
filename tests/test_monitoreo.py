import pandas as pd
from src.monitoreo import evaluar


def fixture_data(tmp_path):
    (tmp_path/'predicciones').mkdir()
    pd.DataFrame({'fecha':['2025-09-01'],'visitantes':[1]}).to_csv(tmp_path/'movilidad_mensual_peten.csv',index=False)
    pd.DataFrame({'fecha':['2025-09-01'],'viajeros_nacionales':[10]}).to_csv(tmp_path/'migracion_nacional_mensual.csv',index=False)
    pd.DataFrame({'fecha':['2026-01-01','2026-02-01'],'subdestino':['Flores']*2,'segmento':['mayor a 1 dia']*2,'visitantes_estimados':[10,11]}).to_csv(tmp_path/'predicciones'/'prediccion_peten_ene_feb_2026.csv',index=False)


def test_alerta_cobertura(tmp_path):
    fixture_data(tmp_path)
    report = evaluar(tmp_path, {'monitoreo': {'meses_movilidad_esperados':['2025-09','2025-10']}})
    assert any('ACTUALIZACION' in a for a in report['alertas'])


def test_alerta_prediccion_negativa(tmp_path):
    fixture_data(tmp_path)
    path = tmp_path/'predicciones'/'prediccion_peten_ene_feb_2026.csv'
    df = pd.read_csv(path)
    df.loc[0,'visitantes_estimados'] = -1
    df.to_csv(path,index=False)
    assert any('CRITICO' in a for a in evaluar(tmp_path, {})['alertas'])


def test_alerta_variacion(tmp_path):
    fixture_data(tmp_path)
    path = tmp_path/'predicciones'/'prediccion_peten_ene_feb_2026.csv'
    df = pd.read_csv(path)
    df.loc[1,'visitantes_estimados'] = 100
    df.to_csv(path,index=False)
    assert any('REVISION' in a for a in evaluar(tmp_path, {'monitoreo': {'variacion_mensual_alerta': 0.75}})['alertas'])
