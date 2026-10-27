"""Pruebas unitarias de reglas de indicadores; no requieren datos institucionales."""
import pandas as pd
import pytest
from src.indicadores import indicadores


def tablas_ejemplo():
    d = pd.Timestamp('2025-09-01')
    return {
        'movilidad_mensual_peten': pd.DataFrame([
            [d,'Isla de Flores','mayor a 1 dia',10.,40.,4.],
            [d,'Isla de Flores','menor a 1 dia',20.,20.,None],
            [d,'El Remate','mayor a 1 dia',5.,15.,3.],
            [d,'El Remate','menor a 1 dia',5.,5.,None],
        ],columns=['fecha','subdestino','segmento','visitantes','dias_persona','estadia_media_dias']),
        'tikal_mensual':pd.DataFrame({'fecha':[d],'nacionales':[20],'extranjeros':[30],'otros':[0],'total':[50]}),
        'aimm_pasajeros_mensual':pd.DataFrame({'fecha':[d],'flujo':['Entrada'],'tipo_pasajero':['Doméstico'],'pasajeros':[100]}),
        'aimm_operaciones_mensual':pd.DataFrame({'fecha':[d],'tipo_operacion':['Aterrizaje'],'operaciones':[3]}),
        'ocupacion_peten':pd.DataFrame({'fecha':[d],'indice_ocupacion':[0.65]}),
        'oferta_hotelera_peten':pd.DataFrame({'anio':[2025],'trimestre':[4],'tipo_alojamiento':['Hotel'],'establecimientos':[2],'habitaciones':[20],'plazas_cama':[40]}),
        'comparacion_fuentes_peten':pd.DataFrame({'fecha':[d],'boletos_tikal':[50],'pasajeros_aimm':[100],'movilidad_poligono_aeropuerto':[150]})
    }

def test_estadia_ponderada_por_poligono():
    r = indicadores(tablas_ejemplo())['estadia_ponderada']
    assert r.loc[r.subdestino.eq('Isla de Flores'),'estadia_media_ponderada_dias'].iloc[0] == 4
    assert r.loc[r.subdestino.eq('El Remate'),'estadia_media_ponderada_dias'].iloc[0] == 3

def test_no_sumar_poligonos():
    r = indicadores(tablas_ejemplo())['visitantes_subdestino']
    assert len(r) == 2
    assert set(r['visitantes']) == {30.,10.}

def test_proporciones():
    r = indicadores(tablas_ejemplo())['segmentacion_visitantes']
    f = r.loc[r.subdestino.eq('Isla de Flores')].iloc[0]
    assert f['proporcion_turistas'] == pytest.approx(1/3)
    assert f['proporcion_excursionistas'] == pytest.approx(2/3)

def test_ocupacion_pct():
    r = indicadores(tablas_ejemplo())['ocupacion_indicadores']
    assert r['ocupacion_pct'].iloc[0] == pytest.approx(65)

def test_indices_base_100():
    r = indicadores(tablas_ejemplo())['comparacion_fuentes_indices']
    assert r['indice_boletos_tikal'].iloc[0] == pytest.approx(100)
    assert r['indice_pasajeros_aimm'].iloc[0] == pytest.approx(100)

def test_rechaza_dias_inconsistentes():
    t = tablas_ejemplo()
    t['movilidad_mensual_peten'].loc[0,'dias_persona'] = 1
    with pytest.raises(ValueError, match='menores'):
        indicadores(t)
