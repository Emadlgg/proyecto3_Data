import numpy as np
import pandas as pd
import pytest
from src.predicciones import perfil_historico
from src.imputacion import (estimar_hueco, backtest, resumen_backtest, imputar, OBJETIVO,
                            METODOS_GUIA)


def sintetico():
    """Factor de reparto lineal en el tiempo: la interpolación debe recuperarlo exacto."""
    f_mig = pd.date_range('2017-01-01', '2026-06-01', freq='MS')
    mig = pd.DataFrame({'fecha': f_mig, 'viajeros_nacionales': [200_000 + 10_000 * f.month for f in f_mig]})
    obs = [f for f in pd.date_range('2025-09-01', '2026-06-01', freq='MS') if f.strftime('%Y-%m') not in ('2026-01', '2026-02')]
    t0 = pd.Timestamp('2025-09-01')
    def factor(f): return 0.10 + 0.005 * ((f.year - t0.year) * 12 + f.month - t0.month)
    nat = mig.set_index('fecha').viajeros_nacionales
    mov = pd.DataFrame({'fecha': obs, 'subdestino': 'A', 'segmento': 'mayor a 1 dia',
                        'visitantes': [factor(f) * nat[f] for f in obs]})
    return mov, mig, factor, nat


def test_interpolacion_recupera_factor_lineal():
    mov, mig, factor, nat = sintetico()
    est = estimar_hueco(mov, nat, perfil_historico(mig), [pd.Timestamp(x) for x in OBJETIVO])
    esperado = [factor(pd.Timestamp(x)) * nat[pd.Timestamp(x)] for x in OBJETIVO]
    assert np.allclose(est['interpolado_observada'], esperado)


def test_imputar_solo_objetivo_y_rotula_estimacion():
    mov, mig, _, _ = sintetico()
    imp = imputar(mov, mig, perfil_historico(mig))
    assert set(imp.fecha.dt.strftime('%Y-%m')) == {'2026-01', '2026-02'}
    assert set(imp.tipo_dato) == {'Estimación'}
    assert imp.principal.sum() == 2 and (imp.visitantes_estimados > 0).all()
    assert set(METODOS_GUIA) <= set(imp.metodo)


def test_imputar_rechaza_si_objetivo_ya_observado():
    mov, mig, _, _ = sintetico()
    extra = mov.iloc[[0]].assign(fecha=pd.Timestamp('2026-01-01'))
    with pytest.raises(ValueError):
        imputar(pd.concat([mov, extra]), mig, perfil_historico(mig))


def test_backtest_reporta_mape_y_error_casi_cero_en_caso_lineal():
    mov, mig, _, _ = sintetico()
    det = backtest(mov, mig, perfil_historico(mig))
    res = resumen_backtest(det).set_index('metodo')
    assert {'MAE', 'RMSE', 'MAPE'} <= set(res.columns)
    assert res.loc['interpolado_observada', 'MAPE'] < 1e-6
