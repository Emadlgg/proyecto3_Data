import pandas as pd
import pytest
from src.encuestas import porcentajes_muestra, satisfaccion_muestra, leer_encuesta


def sample():
    return pd.DataFrame({'SbjNum':[1,2,3], 'Lugar_Turistico':['Flores']*3,
                         'tipo_visitante':['Receptor']*3, 'p05':['F','F','M'],
                         'T_p65':[5,4,None]})


def test_porcentaje_por_respuestas_validas():
    d = porcentajes_muestra(sample(), {'p05':'genero'})
    assert d['porcentaje_muestra'].sum() == pytest.approx(100)
    assert d.loc[d.respuesta.eq('F'), 'porcentaje_muestra'].iloc[0] == pytest.approx(200/3)


def test_no_expande_a_poblacion():
    d = porcentajes_muestra(sample(), {'p05':'genero'})
    assert 'visitantes_estimados' not in d.columns
    assert set(d.n_encuestados) == {3}


def test_satisfaccion_valida():
    dictionary = pd.DataFrame({'columna':['T_p65'], 'pregunta':['Satisfacción general']})
    d = satisfaccion_muestra(sample(), dictionary, ['T_p65'])
    assert d.media_muestra.iloc[0] == 4.5
    assert d.n_respuestas.iloc[0] == 2


def test_satisfaccion_rechaza_fuera_de_rango():
    d = sample(); d.loc[0,'T_p65'] = 6
    with pytest.raises(ValueError, match='fuera de escala'):
        satisfaccion_muestra(d, pd.DataFrame({'columna':['T_p65'],'pregunta':['Satisfacción']}), ['T_p65'])


def test_rechaza_duplicados(tmp_path):
    path = tmp_path/'test.xlsx'; d=sample(); d.loc[1,'SbjNum']=1
    with pd.ExcelWriter(path) as w:
        d.to_excel(w,sheet_name='datos',index=False)
        pd.DataFrame({'columna':['p05'],'pregunta':['Género'],'% respondido':[100]}).to_excel(w,sheet_name='diccionario',index=False)
        pd.DataFrame([['Factor de expansión','NO EXISTE. No son expandibles']]).to_excel(w,sheet_name='nota_metodologica',index=False,header=False)
    with pytest.raises(ValueError,match='repetidos'):
        leer_encuesta(path)
