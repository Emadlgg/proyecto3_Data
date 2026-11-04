import pandas as pd
import pytest
from src.optimizacion_ventanas import preparar, ventanas_validas, evaluar_ventanas


def datos():
    fechas=pd.date_range('2025-09-01',periods=6,freq='MS')
    mov=pd.DataFrame([{'fecha':f,'subdestino':g,'segmento':'mayor a 1 dia','visitantes':100+i*10} for g in ['A','B'] for i,f in enumerate(fechas)])
    mig=pd.DataFrame({'fecha':fechas,'viajeros_nacionales':[1000]*6})
    return mov,mig

def test_ventanas_consecutivas():
    m,n=preparar(*datos())
    v=ventanas_validas(m)
    assert len(v)==3
    assert v.iloc[0]['origen']==pd.Timestamp('2025-10-01')

def test_salto_no_es_cero():
    m,n=datos()
    m=m[~m.fecha.eq(pd.Timestamp('2025-11-01'))]
    m,n=preparar(m,n)
    assert ventanas_validas(m).empty

def test_no_usa_mes_futuro_para_persistencia():
    m,n=datos()
    _,d,_=evaluar_ventanas(m,n)
    v=d[(d.origen==pd.Timestamp('2025-10-01')) & (d.metodo=='persistencia')]
    assert (v.estimado==110).all()
    m.loc[m.fecha.eq(pd.Timestamp('2025-11-01')),'visitantes']=9999
    _,d2,_=evaluar_ventanas(m,n)
    v2=d2[(d2.origen==pd.Timestamp('2025-10-01')) & (d2.metodo=='persistencia')]
    assert (v2.estimado==110).all()

def test_no_duplica_claves():
    m,n=datos()
    with pytest.raises(ValueError,match='duplicadas'):
        preparar(pd.concat([m,m.iloc[[0]]]),n)

def test_reparto_ausente_sin_nacional_futura():
    m,n=datos()
    n=n[n.fecha<=pd.Timestamp('2025-10-01')]
    _,d,_=evaluar_ventanas(m,n)
    assert not d.metodo.str.startswith('reparto_').any()

def test_rmse_y_mae():
    m,n=datos()
    _,d,r=evaluar_ventanas(m,n)
    assert not d.empty
    assert (r.RMSE >= r.MAE-1e-9).all()
