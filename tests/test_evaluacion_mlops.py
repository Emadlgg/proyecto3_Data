import numpy as np
import pandas as pd
from src.evaluacion import evaluar_temporal, decidir_aceptacion


def datos():
    fechas = pd.date_range('2025-09-01', periods=4, freq='MS')
    mov = pd.DataFrame({'fecha': fechas, 'subdestino': ['Flores']*4,
                        'segmento': ['mayor a 1 dia']*4,
                        'visitantes': [100, 120, 110, 130]})
    mig = pd.DataFrame({'fecha': fechas, 'viajeros_nacionales': [1000, 1200, 1100, 1300]})
    perfil = pd.DataFrame({'mes': range(1,13), 'indice': [1.0]*12})
    return mov, mig, perfil


def test_evaluacion_tres_meses():
    detalle, resumen = evaluar_temporal(*datos())
    assert len(detalle) == 3
    assert set(detalle.fecha.dt.month) == {10, 11, 12}
    assert len(resumen) == 1


def test_no_utiliza_mes_evaluado():
    mov, mig, perfil = datos()
    a, _ = evaluar_temporal(mov, mig, perfil)
    mov.loc[mov.fecha.dt.month.eq(12),'visitantes'] = 9000
    b, _ = evaluar_temporal(mov, mig, perfil)
    assert np.isclose(a.loc[a.fecha.dt.month.eq(12),'estimado'].iloc[0],
                      b.loc[b.fecha.dt.month.eq(12),'estimado'].iloc[0])


def test_referencia_ultimo_mes():
    d, _ = evaluar_temporal(*datos())
    assert d.loc[d.fecha.dt.month.eq(10),'referencia'].iloc[0] == 100
    assert d.loc[d.fecha.dt.month.eq(12),'referencia'].iloc[0] == 110


def test_regla_acepta_caso_perfecto():
    d, _ = evaluar_temporal(*datos())
    cfg = {'evaluacion':{'ratio_mae_maximo':1.0,'nmae_maximo':0.35}}
    assert decidir_aceptacion(d,cfg)['aprobado']


def test_regla_rechaza_fallo_calidad():
    d, _ = evaluar_temporal(*datos())
    cfg = {'evaluacion':{'ratio_mae_maximo':1.0,'nmae_maximo':0.35}}
    assert not decidir_aceptacion(d,cfg,calidad_ok=False)['aprobado']


def test_rechaza_duplicados():
    mov, mig, perfil = datos()
    try:
        evaluar_temporal(pd.concat([mov,mov.iloc[[0]]]),mig,perfil)
        assert False
    except ValueError as e:
        assert 'duplicadas' in str(e)
