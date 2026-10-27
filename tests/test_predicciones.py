import numpy as np
import pandas as pd
import pytest
from src.predicciones import perfil_historico, estimar_nacional, estimar_destino, validar_retroactivo


def ejemplo():
    fechas = pd.date_range('2017-01-01','2025-12-01',freq='MS')
    mig = pd.DataFrame({'fecha':fechas,'viajeros_nacionales':[100 + (f.month * 10) for f in fechas]})
    obs = pd.date_range('2025-09-01','2025-12-01',freq='MS')
    mov = pd.DataFrame({'fecha':obs,'subdestino':['Isla de Flores']*4,'segmento':['mayor a 1 dia']*4,
                        'visitantes':[0.1*(100+f.month*10) for f in obs]})
    return mov,mig


def test_perfil_tiene_12_meses_y_media_uno():
    _,mig=ejemplo()
    p=perfil_historico(mig)
    assert len(p)==12
    assert np.isclose(p.indice.mean(),1)


def test_estimaciones_solo_enero_febrero_2026():
    _,mig=ejemplo()
    n=estimar_nacional(mig,perfil_historico(mig),[1,2])
    assert n.fecha.dt.strftime('%Y-%m').tolist()==['2026-01','2026-02']
    assert (n.migracion_nacional_estimada>0).all()


def test_factor_de_reparto_recupera_relacion():
    mov,mig=ejemplo()
    n=estimar_nacional(mig,perfil_historico(mig),[1,2])
    pred,factores=estimar_destino(mov,mig,n)
    assert np.isclose(factores.factor_reparto.iloc[0],0.1)
    assert np.allclose(pred.visitantes_estimados,pred.migracion_nacional_estimada*0.1)
    assert set(pred.tipo_dato)=={'Estimación'}


def test_validacion_fuera_de_muestra():
    mov,mig=ejemplo()
    detalle,metricas=validar_retroactivo(mov,mig)
    assert len(detalle)==4
    assert np.isclose(metricas.MAE.iloc[0],0)
    assert np.isclose(metricas.RMSE.iloc[0],0)


def test_no_acepta_calibracion_incompleta():
    mov,mig=ejemplo()
    n=estimar_nacional(mig,perfil_historico(mig),[1,2])
    with pytest.raises(ValueError,match='cuatro meses'):
        estimar_destino(mov.iloc[:3],mig,n)


def test_validacion_no_usa_mes_evaluado():
    mov,mig=ejemplo()
    # Un valor atípico en un mes no debe alterar la predicción de ese mismo mes
    mov.loc[mov.fecha.dt.month.eq(12),'visitantes']=10000
    detalle,_=validar_retroactivo(mov,mig)
    diciembre=detalle[detalle.fecha.dt.month.eq(12)].iloc[0]
    assert diciembre.estimado < 100
    assert diciembre.observado == 10000
