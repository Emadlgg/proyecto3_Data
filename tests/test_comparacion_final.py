import pandas as pd
import pytest
from src.optimizacion_ventanas import comparacion_justa, comparaciones_finales, evaluar_ventanas


def muestra():
    rows=[]
    for origen, fecha in [('2025-10-01','2025-11-01'),('2025-11-01','2025-12-01')]:
        for metodo, valor in [('persistencia',90),('media_movil',80),('reparto_ultimo',95)]:
            if origen=='2025-11-01' and metodo=='reparto_ultimo':
                continue
            rows.append(dict(origen=origen,fecha=fecha,horizonte=1,subdestino='A',segmento='mayor a 1 dia',metodo=metodo,observado=100,estimado=valor,informacion_nacional_futura=metodo.startswith('reparto_')))
    return pd.DataFrame(rows)


def test_comparacion_operativa_mismas_fechas():
    d,r=comparacion_justa(muestra(),('persistencia','media_movil'))
    assert len(d)==4
    assert r.n.tolist()==[2,2]
    assert not r.requiere_nacional_futura.any()


def test_comparacion_expost_interseccion():
    d,r=comparacion_justa(muestra(),('persistencia','media_movil','reparto_ultimo'))
    assert len(d)==3
    assert (r.n==1).all()
    assert d.origen.nunique()==1


def test_rechaza_duplicados():
    d=muestra()
    with pytest.raises(ValueError,match='duplicadas'):
        comparacion_justa(pd.concat([d,d.iloc[[0]]]),('persistencia','media_movil'))


def test_rechaza_observados_inconsistentes():
    d=muestra()
    d.loc[d.metodo.eq('media_movil') & d.origen.eq('2025-10-01'),'observado']=999
    with pytest.raises(ValueError,match='inconsistentes'):
        comparacion_justa(d,('persistencia','media_movil'))


def test_no_inventa_ventanas_ausentes():
    d,r=comparacion_justa(muestra(),('persistencia','reparto_mediano'))
    assert d.empty and r.empty


def test_metricas_recalculadas():
    d,r=comparacion_justa(muestra(),('persistencia','media_movil'))
    assert r.set_index('metodo').loc['persistencia','MAE']==10
    assert r.set_index('metodo').loc['media_movil','RMSE']==20
