import numpy as np
import pandas as pd
import pytest
from src.optimizacion import evaluar, metricas


def fixtures():
    dates = pd.date_range('2025-09-01',periods=4,freq='MS')
    mov = pd.DataFrame({'fecha':dates,'subdestino':'Flores','segmento':'mayor a 1 dia','visitantes':[10.,12.,13.,15.]})
    mig = pd.DataFrame({'fecha':dates,'viajeros_nacionales':[100.,110.,120.,130.]})
    perfil = pd.DataFrame({'mes':list(range(1,13)),'indice':[1.]*12})
    return mov,mig,perfil


def test_mismos_meses_todos_los_metodos():
    d=evaluar(*fixtures())
    assert len(d)==8
    assert set(d.fecha.dt.month)=={11,12}
    assert d.groupby('metodo').size().nunique()==1


def test_no_utiliza_observacion_objetivo():
    mov,mig,p=fixtures()
    first=evaluar(mov,mig,p)
    mov.loc[mov.fecha.dt.month.eq(12),'visitantes']=9999.
    second=evaluar(mov,mig,p)
    a=first[first.fecha.dt.month.eq(12)].set_index('metodo').estimado
    b=second[second.fecha.dt.month.eq(12)].set_index('metodo').estimado
    pd.testing.assert_series_equal(a,b)


def test_no_utiliza_migracion_del_mes_objetivo():
    mov,mig,p=fixtures()
    first=evaluar(mov,mig,p)
    mig.loc[mig.fecha.dt.month.eq(12),'viajeros_nacionales']=99999.
    second=evaluar(mov,mig,p)
    a=first[first.fecha.dt.month.eq(12)].set_index('metodo').estimado
    b=second[second.fecha.dt.month.eq(12)].set_index('metodo').estimado
    pd.testing.assert_series_equal(a,b)


def test_rechaza_duplicados():
    mov,mig,p=fixtures()
    with pytest.raises(ValueError,match='duplicadas'):
        evaluar(pd.concat([mov,mov.iloc[[0]]]),mig,p)


def test_metricas_correctas():
    d=evaluar(*fixtures()); m=metricas(d)
    assert len(m)==4
    assert (m.MAE>=0).all() and np.isfinite(m.RMSE).all()
    assert (m.n==2).all()


def test_rechaza_cobertura_incompleta():
    mov,mig,p=fixtures()
    with pytest.raises(ValueError,match='discontinua'):
        evaluar(mov.drop(index=1),mig,p)
