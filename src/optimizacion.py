"""Diagnóstico temporal de métodos candidatos. No publica ni modifica el pipeline.

Uso: python -m src.optimizacion --data data/processed
La validación es de un paso hacia adelante; nunca utiliza el mes objetivo.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('persistencia', 'media_movil', 'reparto_ultimo', 'reparto_mediano')


def _check(mov: pd.DataFrame, mig: pd.DataFrame, perfil: pd.DataFrame) -> None:
    required = {'fecha','subdestino','segmento','visitantes'}
    if not required.issubset(mov):
        raise ValueError(f'Movilidad: faltan {sorted(required-set(mov))}')
    if not {'fecha','viajeros_nacionales'}.issubset(mig):
        raise ValueError('Migración: faltan columnas')
    if not {'mes','indice'}.issubset(perfil):
        raise ValueError('Perfil: faltan mes e indice')
    for df in (mov, mig):
        if not pd.api.types.is_datetime64_any_dtype(df.fecha):
            raise ValueError('fecha debe ser datetime')
    if mov.duplicated(['fecha','subdestino','segmento']).any() or mig.fecha.duplicated().any():
        raise ValueError('Claves duplicadas')
    for s in (mov.visitantes, mig.viajeros_nacionales, perfil.indice):
        x = pd.to_numeric(s, errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(x).all() or (x < 0).any():
            raise ValueError('Valor no finito, faltante o negativo')
    if (mig.viajeros_nacionales <= 0).any() or (perfil.indice <= 0).any():
        raise ValueError('Denominador o indice no positivo')
    if perfil.mes.duplicated().any() or set(perfil.mes) != set(range(1,13)):
        raise ValueError('Perfil debe tener los 12 meses sin duplicados')


def evaluar(mov: pd.DataFrame, mig: pd.DataFrame, perfil: pd.DataFrame,
            min_entrenamiento: int = 2) -> pd.DataFrame:
    """Backtesting expanding-window con pronóstico de migración también sin futuro.

    Para cada mes t, estima nivel nacional usando SOLO migración de meses previos,
    y factor de reparto usando SOLO movilidad de meses previos.
    """
    _check(mov, mig, perfil)
    if min_entrenamiento < 2:
        raise ValueError('Se requieren al menos dos meses de entrenamiento')
    mov = mov.copy().sort_values('fecha')
    mig = mig.copy().sort_values('fecha')
    p = perfil.set_index('mes')['indice'].astype(float)
    nat = mig.set_index('fecha')['viajeros_nacionales'].astype(float)
    rows = []
    for (sub, seg), g in mov.groupby(['subdestino','segmento']):
        g = g.sort_values('fecha')
        # Exigir meses consecutivos en cada grupo para una evaluación honesta.
        periods = g.fecha.dt.to_period('M')
        if len(periods) != len(pd.period_range(periods.iloc[0], periods.iloc[-1], freq='M')):
            raise ValueError(f'Cobertura mensual discontinua: {sub}, {seg}')
        for i in range(min_entrenamiento, len(g)):
            train = g.iloc[:i]
            target = g.iloc[i]
            t = target.fecha
            prev_nat = nat.reindex(train.fecha)
            if prev_nat.isna().any() or (prev_nat <= 0).any():
                raise ValueError('Migración histórica faltante en calibración')
            # Nivel nacional histórico ajustado por índice estacional; sin usar nacional del mes t.
            prior_indices = train.fecha.dt.month.map(p).to_numpy(dtype=float)
            nivel = float(np.median(prev_nat.to_numpy() / prior_indices))
            nacional_pronosticada = nivel * float(p.loc[t.month])
            ratios = train.visitantes.to_numpy(dtype=float) / prev_nat.to_numpy(dtype=float)
            candidates = {
                'persistencia': float(train.visitantes.iloc[-1]),
                'media_movil': float(train.visitantes.tail(3).mean()),
                'reparto_ultimo': float(ratios[-1] * nacional_pronosticada),
                'reparto_mediano': float(np.median(ratios) * nacional_pronosticada),
            }
            for method, estimate in candidates.items():
                rows.append(dict(fecha=t, subdestino=sub, segmento=seg, metodo=method,
                                 observado=float(target.visitantes), estimado=estimate,
                                 error=estimate-float(target.visitantes),
                                 n_entrenamiento=i, ultimo_mes_entrenamiento=train.fecha.iloc[-1],
                                 nacional_estimado=nacional_pronosticada))
    if not rows:
        raise ValueError('Sin meses suficientes para evaluar')
    return pd.DataFrame(rows).sort_values(['fecha','subdestino','segmento','metodo']).reset_index(drop=True)


def metricas(detalle: pd.DataFrame) -> pd.DataFrame:
    if detalle.empty:
        raise ValueError('Evaluación vacía')
    out = []
    for method, g in detalle.groupby('metodo'):
        e = g.error.to_numpy(dtype=float)
        out.append(dict(metodo=method, n=len(g), MAE=float(np.mean(np.abs(e))),
                        RMSE=float(np.sqrt(np.mean(e**2)))))
    return pd.DataFrame(out).sort_values(['MAE','metodo']).reset_index(drop=True)


def ejecutar(data: Path, output: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    mov = pd.read_csv(data/'movilidad_mensual_peten.csv', parse_dates=['fecha'])
    mig = pd.read_csv(data/'migracion_nacional_mensual.csv', parse_dates=['fecha'])
    perfil = pd.read_csv(data/'predicciones'/'perfil_estacional_nacional.csv')
    # Ventana comparable de meses observados, sin mezclar 2026 con calibración 2025.
    mov = mov[(mov.fecha.dt.year == 2025) & mov.fecha.dt.month.isin([9,10,11,12])].copy()
    detalle = evaluar(mov,mig,perfil)
    resumen = metricas(detalle)
    output.mkdir(parents=True,exist_ok=True)
    detalle.to_csv(output/'diagnostico_temporal.csv',index=False)
    resumen.to_csv(output/'comparacion_modelos.csv',index=False)
    return detalle,resumen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'data'/'processed')
    parser.add_argument('--out',type=Path,default=ROOT/'data'/'processed'/'optimizacion')
    parser.add_argument('--horizonte',type=int,choices=[1,2],default=1,help='1: diagnostico anterior; 2: dos meses sin actualizar con observaciones')
    args=parser.parse_args()
    d,m=(ejecutar_horizonte_dos(args.data,args.out) if args.horizonte == 2 else ejecutar(args.data,args.out))
    print(f'Evaluaciones: {len(d)} | Meses: {d.fecha.dt.strftime("%Y-%m").unique().tolist()}')
    print(m.to_string(index=False))
    print('Diagnóstico exploratorio: NO modifica el modelo aprobado ni publica resultados.')



# -----------------------------------------------------------------------------
# Diagnostico de horizonte fijo de DOS meses. No modifica el metodo oficial.
# -----------------------------------------------------------------------------
def _perfil_historico(mig: pd.DataFrame, corte: pd.Timestamp) -> pd.Series:
    """Indices estacionales estimados exclusivamente con anios COMPLETOS previos al corte.

    Cada anio aporta 12 meses; el indice de cada mes es su valor dividido
    entre el promedio de ese mismo anio. Evita utilizar datos futuros.
    """
    previo = mig.loc[mig.fecha < corte, ['fecha', 'viajeros_nacionales']].copy()
    previo['anio'] = previo.fecha.dt.year
    previo['mes'] = previo.fecha.dt.month
    completos = previo.groupby('anio').filter(lambda x: len(x) == 12 and set(x.mes) == set(range(1, 13)))
    if completos.empty:
        raise ValueError('Sin anios nacionales completos anteriores al corte')
    completos['relativo'] = completos.viajeros_nacionales / completos.groupby('anio').viajeros_nacionales.transform('mean')
    p = completos.groupby('mes').relativo.mean().reindex(range(1,13))
    if p.isna().any() or (p <= 0).any():
        raise ValueError('Perfil estacional incompleto')
    return p / p.mean()


def evaluar_horizonte_dos(mov: pd.DataFrame, mig: pd.DataFrame,
                          min_entrenamiento: int = 2) -> pd.DataFrame:
    """Pronostica t+1 y t+2 desde un MISMO origen, sin usar t+1 para t+2.

    Usa solo movilidad anterior o igual al origen y migracion nacional
    anterior o igual al origen. No utiliza perfil precalculado con futuro.
    """
    mov = mov.copy()
    mig = mig.copy()
    mov['fecha'] = pd.to_datetime(mov['fecha'], errors='coerce')
    mig['fecha'] = pd.to_datetime(mig['fecha'], errors='coerce')
    if mov.fecha.isna().any() or mig.fecha.isna().any():
        raise ValueError('Fechas invalidas')
    required_mov = {'fecha','subdestino','segmento','visitantes'}
    if not required_mov.issubset(mov) or not {'fecha','viajeros_nacionales'}.issubset(mig):
        raise ValueError('Columnas requeridas ausentes')
    if mov.duplicated(['fecha','subdestino','segmento']).any() or mig.fecha.duplicated().any():
        raise ValueError('Fechas o claves duplicadas')
    for df,col in ((mov,'visitantes'),(mig,'viajeros_nacionales')):
        vals = pd.to_numeric(df[col],errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(vals).all() or (vals < 0).any():
            raise ValueError(f'{col} invalido')
    if (mig.viajeros_nacionales <= 0).any():
        raise ValueError('Denominador nacional no positivo')
    if min_entrenamiento < 2:
        raise ValueError('min_entrenamiento debe ser al menos 2')
    mig = mig.sort_values('fecha')
    nat = mig.set_index('fecha').viajeros_nacionales
    rows = []
    for (sub,seg), g in mov.groupby(['subdestino','segmento']):
        g = g.sort_values('fecha').reset_index(drop=True)
        periodos = g.fecha.dt.to_period('M')
        if len(periodos) != len(pd.period_range(periodos.iloc[0],periodos.iloc[-1],freq='M')):
            raise ValueError(f'Cobertura discontinua: {sub}/{seg}')
        for i in range(min_entrenamiento - 1, len(g)-2):
            train = g.iloc[:i+1]
            origen = train.fecha.iloc[-1]
            futuros = g.iloc[i+1:i+3]
            if any((futuros.fecha.iloc[j].to_period('M') - origen.to_period('M')).n != j+1 for j in range(2)):
                raise ValueError('Horizonte no consecutivo')
            previo_nat = nat.reindex(train.fecha)
            if previo_nat.isna().any() or (previo_nat <= 0).any():
                raise ValueError('Migracion ausente en entrenamiento')
            perfil = _perfil_historico(mig, pd.Timestamp(origen) + pd.Timedelta(days=1))
            indices_train = train.fecha.dt.month.map(perfil).to_numpy(dtype=float)
            nivel = float(np.median(previo_nat.to_numpy(dtype=float) / indices_train))
            ratios = train.visitantes.to_numpy(dtype=float) / previo_nat.to_numpy(dtype=float)
            for h in (1,2):
                target = futuros.iloc[h-1]
                nacional = nivel * float(perfil.loc[target.fecha.month])
                estimates = {
                    'persistencia': float(train.visitantes.iloc[-1]),
                    'media_movil': float(train.visitantes.tail(3).mean()),
                    'reparto_ultimo': float(ratios[-1] * nacional),
                    'reparto_mediano': float(np.median(ratios) * nacional),
                }
                for metodo, estimado in estimates.items():
                    rows.append({'origen': origen, 'fecha':target.fecha, 'horizonte':h,
                                 'subdestino':sub,'segmento':seg,'metodo':metodo,
                                 'observado':float(target.visitantes),'estimado':estimado,
                                 'error':estimado-float(target.visitantes),
                                 'n_entrenamiento':len(train),'nacional_estimado':nacional})
    if not rows:
        raise ValueError('No existen ventanas de dos meses con entrenamiento suficiente')
    return pd.DataFrame(rows).sort_values(['origen','fecha','subdestino','segmento','metodo']).reset_index(drop=True)


def ejecutar_horizonte_dos(data: Path, output: Path) -> tuple[pd.DataFrame,pd.DataFrame]:
    mov = pd.read_csv(data/'movilidad_mensual_peten.csv',parse_dates=['fecha'])
    mig = pd.read_csv(data/'migracion_nacional_mensual.csv',parse_dates=['fecha'])
    # El archivo incluye una segunda ventana 2026; no mezclar con 2025.
    mov = mov.loc[(mov.fecha.dt.year == 2025) & mov.fecha.dt.month.isin([9,10,11,12])].copy()
    detalle = evaluar_horizonte_dos(mov,mig)
    resumen = metricas(detalle)
    output.mkdir(parents=True,exist_ok=True)
    detalle.to_csv(output/'diagnostico_horizonte2.csv',index=False)
    resumen.to_csv(output/'comparacion_horizonte2.csv',index=False)
    return detalle,resumen

if __name__=='__main__':
    main()
