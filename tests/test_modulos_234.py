import pandas as pd
import numpy as np
from src.visualizaciones_extra import serie_diaria, patron_semanal, lift_eventos, comparacion_indices, ocupacion_y_afluencia


def test_serie_diaria_no_mezcla_subdestinos():
    df = pd.DataFrame({'fecha':pd.to_datetime(['2025-09-01']*3), 'subdestino':['A','A','B'],
                       'evento':['X','Y','X'],'presencias_diarias':[10,5,200]})
    out = serie_diaria(df, 'A')
    assert len(out) == 1 and out.presencias_diarias.iloc[0] == 15


def test_patron_semanal_media_por_fecha():
    df = pd.DataFrame({'fecha':pd.to_datetime(['2025-09-01','2025-09-08']), 'presencias_diarias':[10,30]})
    assert patron_semanal(df).presencias_diarias.iloc[0] == 20


def test_lift_sin_referencia_no_inventa_valor():
    df = pd.DataFrame({'fecha':pd.to_datetime(['2025-09-01']), 'evento':['Feriado'], 'presencias_diarias':[100]})
    assert np.isnan(lift_eventos(df).lift_pct.iloc[0])


def test_indices_no_suman_universos():
    d = pd.DataFrame({'fecha':pd.to_datetime(['2025-09-01']), 'indice_boletos_tikal':[100],
                      'indice_pasajeros_aimm':[100], 'indice_movilidad_poligono_aeropuerto':[100]})
    out = comparacion_indices(d)
    assert len(out) == 3 and set(out.indice) == {100}


def test_cruce_solo_cuatro_meses_2025():
    f = pd.to_datetime(['2025-08-01','2025-09-01','2025-12-01','2026-01-01'])
    a = pd.DataFrame({'fecha':f,'ocupacion_pct':[50,60,70,80]})
    b = pd.DataFrame({'fecha':f,'total':[10,20,30,40]})
    out = ocupacion_y_afluencia(a,b)
    assert out.fecha.dt.month.tolist() == [9,12]


def test_lift_regular_mismo_dia_semana():
    d = pd.DataFrame({'fecha':pd.to_datetime(['2025-09-01','2025-09-08']),
                      'evento':['Regular','Feriado'],'presencias_diarias':[100,125]})
    out = lift_eventos(d)
    assert round(out.lift_pct.iloc[0], 3) == 25.0
