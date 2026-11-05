import pandas as pd
import pytest
from src.mercados_emisores import procesar, top_mercados


def muestra():
    return pd.DataFrame([
        ('Flores','Guatemala','2025-09-01',10,'mayor a 1 dia'),
        ('Flores','Guatemala','2025-09-01',5,'menor a 1 dia'),
        ('Flores','Belice','2025-09-01',3,'mayor a 1 dia'),
        ('Remate','Belice','2025-09-01',100,'mayor a 1 dia'),
        ('Flores','Mexico','2025-10-01',7,'menor a 1 dia'),
    ], columns=['destino','pais','fecha','visitantes','es_consecutivo'])


def test_consolida_segmentos_sin_sumar_poligonos():
    d = procesar(muestra())
    assert d.loc[(d.subdestino=='Flores') & (d.pais=='Guatemala'),'visitantes'].iloc[0] == 15
    assert d.loc[(d.subdestino=='Remate') & (d.pais=='Belice'),'visitantes'].iloc[0] == 100


def test_separa_nacionales_extranjeros():
    d = procesar(muestra())
    assert set(d.loc[d.pais=='Guatemala','mercado']) == {'Nacional'}
    assert set(d.loc[d.pais=='Belice','mercado']) == {'Extranjero'}


def test_top_no_mezcla_poligonos():
    d = procesar(muestra())
    t = top_mercados(d, 'Flores')
    assert t.pais.tolist() == ['Mexico','Belice']
    assert t.visitantes.sum() == 10


def test_rechaza_negativos():
    d = muestra()
    d.loc[0,'visitantes'] = -1
    with pytest.raises(ValueError):
        procesar(d)


def test_rechaza_columnas_faltantes():
    with pytest.raises(ValueError):
        procesar(muestra().drop(columns='pais'))
