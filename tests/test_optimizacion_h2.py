import numpy as np
import pandas as pd
import pytest
from src.optimizacion import evaluar_horizonte_dos, metricas


def datos():
    fechas = pd.date_range('2024-01-01',periods=24,freq='MS')
    mig = pd.DataFrame({'fecha':fechas,'viajeros_nacionales':np.full(24,1000.)})
    fechas_m = pd.date_range('2025-09-01',periods=4,freq='MS')
    mov = pd.DataFrame({'fecha':fechas_m,'subdestino':['Flores']*4,
                        'segmento':['mayor a 1 dia']*4,'visitantes':[10.,20.,30.,40.]})
    return mov,mig


def test_dos_meses_mismo_origen():
    mov,mig=datos()
    d=evaluar_horizonte_dos(mov,mig)
    assert set(d.horizonte)=={1,2}
    assert d.origen.nunique()==1
    assert str(d.origen.iloc[0].date())=='2025-10-01'
    assert len(d)==8


def test_persistencia_no_usa_primer_mes_real_para_segundo():
    mov,mig=datos()
    d=evaluar_horizonte_dos(mov,mig)
    p=d[d.metodo=='persistencia'].sort_values('horizonte')
    assert p.estimado.tolist()==[20.,20.]
    assert p.observado.tolist()==[30.,40.]


def test_no_usa_migracion_futura():
    mov,mig=datos()
    a=evaluar_horizonte_dos(mov,mig)
    mig.loc[mig.fecha >= pd.Timestamp('2025-11-01'),'viajeros_nacionales']=1000000.
    b=evaluar_horizonte_dos(mov,mig)
    pd.testing.assert_frame_equal(a,b)


def test_no_usa_movilidad_futura_en_estimaciones():
    mov,mig=datos()
    a=evaluar_horizonte_dos(mov,mig)
    mov.loc[mov.fecha >= pd.Timestamp('2025-11-01'),'visitantes']=[300.,400.]
    b=evaluar_horizonte_dos(mov,mig)
    assert np.allclose(a.estimado,b.estimado)


def test_rechaza_serie_incompleta():
    mov,mig=datos()
    with pytest.raises(ValueError,match='discontinua'):
        evaluar_horizonte_dos(mov.drop(index=1),mig)


def test_metricas_por_metodo():
    mov,mig=datos()
    r=metricas(evaluar_horizonte_dos(mov,mig))
    assert len(r)==4 and (r.n==2).all()
