import pandas as pd
import pytest
from src.predicciones_candidatas import estimar_persistencia
from src.evaluacion_candidatas import evaluar_cortes


def ejemplo():
    return pd.DataFrame([
        {'fecha': f'{m}-01', 'subdestino': d, 'segmento': 'mayor a 1 dia', 'visitantes': v}
        for d, vals in [('Flores', [10, 20, 30, 40]), ('Remate', [5, 8, 9, 11])]
        for m, v in zip(['2025-09', '2025-10', '2025-11', '2025-12'], vals)
    ])


def test_dos_meses_y_seis_o_menos_grupos():
    r = estimar_persistencia(ejemplo())
    assert len(r) == 4
    assert set(r.fecha.dt.strftime('%Y-%m')) == {'2026-01', '2026-02'}


def test_no_usa_valores_posteriores_al_corte():
    d = ejemplo()
    a = estimar_persistencia(d)
    futuro = pd.DataFrame([{'fecha': '2026-03-01', 'subdestino': 'Flores', 'segmento': 'mayor a 1 dia', 'visitantes': 999999}])
    b = estimar_persistencia(pd.concat([d, futuro], ignore_index=True))
    pd.testing.assert_frame_equal(a, b)


def test_persistencia_ambos_horizontes():
    r = estimar_persistencia(ejemplo())
    assert r.loc[r.subdestino.eq('Flores'), 'visitantes_estimados'].tolist() == [40., 40.]


def test_rechaza_corte_incompleto():
    with pytest.raises(ValueError):
        estimar_persistencia(ejemplo().query("subdestino != 'Remate' or fecha != '2025-12-01'"))


def test_rechaza_objetivos_no_consecutivos():
    with pytest.raises(ValueError):
        estimar_persistencia(ejemplo(), objetivos=('2026-01-01', '2026-03-01'))


def test_evaluacion_empata_con_referencia_sin_aprobar():
    detalle, r = evaluar_cortes(ejemplo(), cortes=['2025-10-01'])
    assert len(detalle) == 4
    assert r['MAE_modelo'] == r['MAE_referencia']
    assert r['ratio_mae'] == 1.0
    assert r['aprobacion_automatica'] is False
