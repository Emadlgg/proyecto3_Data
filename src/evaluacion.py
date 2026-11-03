"""Evaluacion temporal estricta para el procedimiento de reparto de Peten.

Para cada mes de prueba, utiliza SOLO observaciones anteriores para estimar
el nivel nacional y el factor de reparto. Compara contra ultimo valor observado.
No usa observaciones del mes de prueba en el ajuste.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def evaluar_temporal(mov: pd.DataFrame, mig: pd.DataFrame, perfil: pd.DataFrame,
                     meses=(10, 11, 12), anio=2025) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_mov = {'fecha', 'subdestino', 'segmento', 'visitantes'}
    required_mig = {'fecha', 'viajeros_nacionales'}
    required_profile = {'mes', 'indice'}
    if not required_mov.issubset(mov) or not required_mig.issubset(mig) or not required_profile.issubset(perfil):
        raise ValueError('Faltan columnas de evaluacion')
    mov, mig, perfil = mov.copy(), mig.copy(), perfil.copy()
    mov['fecha'] = pd.to_datetime(mov.fecha, errors='raise')
    mig['fecha'] = pd.to_datetime(mig.fecha, errors='raise')
    if mov.duplicated(['fecha','subdestino','segmento']).any() or mig.fecha.duplicated().any():
        raise ValueError('Claves duplicadas')
    if perfil.mes.duplicated().any() or len(perfil) != 12:
        raise ValueError('Perfil estacional incompleto o duplicado')
    if not np.isfinite(pd.to_numeric(perfil.indice, errors='coerce')).all() or (perfil.indice <= 0).any():
        raise ValueError('Indices estacionales invalidos')
    if (pd.to_numeric(mig.viajeros_nacionales, errors='coerce') <= 0).any():
        raise ValueError('Denominador nacional no positivo')
    if not np.isfinite(pd.to_numeric(mov.visitantes, errors='coerce')).all() or (mov.visitantes < 0).any():
        raise ValueError('Visitantes invalidos')
    mig = mig.assign(mes=mig.fecha.dt.month).merge(perfil[['mes','indice']],on='mes',validate='many_to_one')
    filas = []
    for (sub, seg), grupo in mov.groupby(['subdestino','segmento']):
        grupo = grupo.sort_values('fecha')
        for mes in meses:
            fecha = pd.Timestamp(anio, int(mes), 1)
            actual = grupo.loc[grupo.fecha.eq(fecha)]
            if len(actual) != 1:
                raise ValueError(f'Falta observacion evaluada: {sub}/{seg}/{fecha.date()}')
            prev = grupo[(grupo.fecha >= pd.Timestamp(anio, 9, 1)) & (grupo.fecha < fecha)].copy()
            prev_nat = mig[(mig.fecha >= pd.Timestamp(anio, 9, 1)) & (mig.fecha < fecha)]
            if prev.empty or prev_nat.empty or prev.fecha.nunique() != prev_nat.fecha.nunique():
                raise ValueError('Historia insuficiente o desalineada')
            train = prev.merge(prev_nat[['fecha','viajeros_nacionales']],on='fecha',validate='one_to_one')
            factor = float(np.median(train.visitantes / train.viajeros_nacionales))
            nivel = float(np.median(prev_nat.viajeros_nacionales / prev_nat.indice))
            idx = perfil.loc[perfil.mes.eq(mes), 'indice']
            if len(idx) != 1:
                raise ValueError('Mes ausente del perfil')
            estimado = factor * nivel * float(idx.iloc[0])
            referencia = float(prev.iloc[-1].visitantes)
            observado = float(actual.iloc[0].visitantes)
            if not np.isfinite([estimado, referencia, observado]).all():
                raise ValueError('Resultado no finito')
            filas.append(dict(fecha=fecha, subdestino=sub, segmento=seg,
                              observado=observado, estimado=estimado,
                              referencia=referencia, fecha_ultimo_ajuste=prev.fecha.max(),
                              meses_ajuste=prev.fecha.nunique()))
    detalle = pd.DataFrame(filas).sort_values(['fecha','subdestino','segmento']).reset_index(drop=True)
    for tipo, col in [('modelo','estimado'), ('referencia','referencia')]:
        detalle[f'error_{tipo}'] = detalle[col] - detalle.observado
    def metricas(g):
        return pd.Series({
            'MAE_modelo': float(np.mean(np.abs(g.error_modelo))),
            'RMSE_modelo': float(np.sqrt(np.mean(g.error_modelo ** 2))),
            'MAE_referencia': float(np.mean(np.abs(g.error_referencia))),
            'RMSE_referencia': float(np.sqrt(np.mean(g.error_referencia ** 2))),
            'meses_evaluados': len(g)
        })
    resumen = detalle.groupby(['subdestino','segmento']).apply(metricas, include_groups=False).reset_index()
    return detalle, resumen


def decidir_aceptacion(detalle: pd.DataFrame, cfg: dict, calidad_ok=True, salidas_ok=True) -> dict:
    """Umbrales fijados antes de ejecutar; sin alterar reglas tras ver resultados."""
    ev = cfg['evaluacion']
    ratio_max = float(ev['ratio_mae_maximo'])
    nmae_max = float(ev['nmae_maximo'])
    if ratio_max <= 0 or nmae_max <= 0:
        raise ValueError('Umbrales deben ser positivos')
    if detalle.empty or not calidad_ok or not salidas_ok:
        return {'aprobado': False, 'razon': 'Calidad, salidas o evaluacion insuficientes'}
    mae_modelo = float(np.mean(np.abs(detalle.error_modelo)))
    mae_ref = float(np.mean(np.abs(detalle.error_referencia)))
    ratio = mae_modelo / mae_ref if mae_ref > 0 else (0.0 if mae_modelo == 0 else float('inf'))
    escala = float(np.median(detalle.observado))
    nmae = mae_modelo / escala if escala > 0 else float('inf')
    aprobado = bool(np.isfinite(mae_modelo) and ratio <= ratio_max and nmae <= nmae_max)
    return {'aprobado': aprobado, 'MAE_modelo': mae_modelo,
            'MAE_referencia': mae_ref, 'ratio_mae': ratio,
            'nMAE': nmae, 'umbral_ratio': ratio_max, 'umbral_nmae': nmae_max,
            'razon': 'Regla satisfecha' if aprobado else 'No cumple umbrales predefinidos'}
