import pandas as pd
from src.visualizaciones import serie_subdestinos, estadia_subdestinos, segmentos, participacion


def ejemplo():
    return pd.DataFrame({'fecha': pd.to_datetime(['2025-09-01','2025-09-01']),
                         'subdestino':['Flores','Aeropuerto'], 'visitantes':[20,10],
                         'estadia_media_ponderada_dias':[2.5,3.0],
                         'turistas_pernocta':[12,6], 'excursionistas':[8,4],
                         'proporcion_turistas':[.6,.6], 'proporcion_excursionistas':[.4,.4]})


def test_serie_no_suma_poligonos():
    fig = serie_subdestinos(ejemplo())
    assert len(fig.data) == 2
    assert sum(sum(trace.y) for trace in fig.data) == 30


def test_estadia_por_subdestino():
    assert len(estadia_subdestinos(ejemplo()).data) == 2


def test_segmentos():
    assert len(segmentos(ejemplo(), 'Flores').data) == 2


def test_participacion():
    assert len(participacion(ejemplo(), '2025-09-01').data) == 2
