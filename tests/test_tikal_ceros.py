"""Los totales cero de Tikal son «sin dato» con motivo documentado; no son visitas medidas en cero."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import etl

RAW = Path(__file__).resolve().parents[1] / 'data' / 'raw'


@pytest.mark.skipif(not (RAW / 'Visitantes_Tikal_2017-2026.xlsx').exists(), reason='sin datos originales')
def test_ceros_de_tikal_tienen_motivo_documentado():
    t = etl.tikal(RAW)
    ceros = t[t.advertencia_cero]
    assert len(ceros) == 7
    assert set(ceros.motivo_cero) == {'cierre_covid19', 'sin_registro_inicio_serie'}  # ninguno sin_clasificar
    assert ceros.loc[ceros.motivo_cero.eq('cierre_covid19'), 'fecha'].dt.strftime('%Y-%m').tolist() == \
        ['2020-04', '2020-05', '2020-06', '2020-07', '2020-08', '2020-09']
    assert t.loc[t.fecha.eq('2017-02-01'), 'registro_parcial'].item()


def test_cero_nuevo_queda_sin_clasificar():
    df = pd.DataFrame({'fecha': pd.to_datetime(['2024-05-01']), 'total': [0]})
    clave = df.fecha.dt.strftime('%Y-%m-%d')
    motivo = clave.map(etl.TIKAL_MOTIVO_CERO).fillna('sin_clasificar')
    assert motivo.item() == 'sin_clasificar'


PROC = Path(__file__).resolve().parents[1] / 'data' / 'processed'


@pytest.mark.skipif(not (RAW / 'Visitantes_Tikal_2017-2026.xlsx').exists() or not (PROC / 'aimm_pasajeros_mensual.csv').exists(),
                    reason='sin datos originales/procesados')
def test_variacion_interanual_no_usa_ceros_ni_parciales_como_base():
    from src import indicadores
    tablas = indicadores.cargar(PROC)
    tablas['tikal_mensual'] = etl.tikal(RAW)          # versión con motivo_cero / registro_parcial
    tik = indicadores.indicadores(tablas)['tikal_indicadores'].set_index('fecha')
    v = tik['variacion_interanual_pct']
    assert v.loc['2020-04-01':'2020-09-01'].isna().all()   # no -100 % por cierre
    assert np.isnan(v.loc['2018-02-01'])                    # base parcial feb-2017: no +2,176 %
    assert v.loc['2021-04-01':'2021-09-01'].isna().all()  # base cerrada
    assert v.loc['2020-10-01'] < 0                           # oct-2020 vs oct-2019 sigue siendo comparable
