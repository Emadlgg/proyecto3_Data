"""Pruebas de controles críticos del pipeline inicial (sin datos privados)."""
import pandas as pd
import pytest
from src.pipeline import control_critico


def base():
    return pd.DataFrame({'fecha':['2025-09-01','2025-10-01'], 'id':['A','A'], 'visitantes':[10,12]})


def check(df):
    control_critico(df, ('fecha','id','visitantes'), ('fecha','id'), ('visitantes',), 'prueba')


def test_valido():
    check(base())

@pytest.mark.parametrize('cambio', ['columna','fecha','duplicado','nulo','negativo','infinito'])
def test_rechaza_dato_critico(cambio):
    df = base()
    if cambio == 'columna': df = df.drop(columns='visitantes')
    if cambio == 'fecha': df.loc[0,'fecha'] = 'fecha_mala'
    if cambio == 'duplicado': df.loc[1,'fecha'] = df.loc[0,'fecha']
    if cambio == 'nulo': df.loc[0,'visitantes'] = None
    if cambio == 'negativo': df.loc[0,'visitantes'] = -1
    if cambio == 'infinito': df.loc[0,'visitantes'] = float('inf')
    with pytest.raises(ValueError):
        check(df)
