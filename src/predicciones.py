"""Estimación exploratoria de movilidad en Petén (enero-febrero 2026).

Método: perfil estacional histórico de migración nacional (2017-2024),
anclaje al nivel nacional sep-dic 2025, y factor de reparto por polígono
/segmento calibrado exclusivamente con telefonía sep-dic 2025.
No extrapolar ni sumar polígonos para obtener un total único de Petén.
Uso: python -m src.predicciones
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROCESSED = BASE / 'data' / 'processed'
OUT = PROCESSED / 'predicciones'


def cargar(directorio: Path = PROCESSED) -> tuple[pd.DataFrame, pd.DataFrame]:
    mov = pd.read_csv(directorio / 'movilidad_mensual_peten.csv', parse_dates=['fecha'])
    mig = pd.read_csv(directorio / 'migracion_nacional_mensual.csv', parse_dates=['fecha'])
    for df, cols in [(mov, ['fecha','subdestino','segmento','visitantes']),
                     (mig, ['fecha','viajeros_nacionales'])]:
        if not set(cols).issubset(df.columns):
            raise ValueError(f'Columnas requeridas ausentes: {set(cols)-set(df.columns)}')
    for df, col in [(mov,'visitantes'),(mig,'viajeros_nacionales')]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].isna().any() or (df[col] < 0).any():
            raise ValueError(f'{col}: faltantes, no numéricos o negativos')
    if mov.duplicated(['fecha','subdestino','segmento']).any():
        raise ValueError('Movilidad: claves duplicadas')
    if mig.fecha.duplicated().any():
        raise ValueError('Migración: fechas duplicadas')
    return mov, mig


def perfil_historico(mig: pd.DataFrame, inicio: int = 2017, fin: int = 2024) -> pd.DataFrame:
    """Índices mensuales relativos al promedio de cada año completo."""
    d = mig.copy()
    d['anio'] = d.fecha.dt.year
    d['mes'] = d.fecha.dt.month
    d = d[d.anio.between(inicio,fin)].copy()
    completos = d.groupby('anio').mes.nunique()
    d = d[d.anio.isin(completos[completos == 12].index)]
    if d.anio.nunique() < 3:
        raise ValueError('Se requieren al menos tres años históricos completos')
    medias = d.groupby('anio').viajeros_nacionales.transform('mean')
    if (medias <= 0).any():
        raise ValueError('Migración histórica: promedios no positivos')
    d['indice'] = d.viajeros_nacionales / medias
    perfil = d.groupby('mes',as_index=False).indice.mean()
    perfil['indice'] = perfil.indice / perfil.indice.mean()
    if len(perfil) != 12 or (perfil.indice <= 0).any():
        raise ValueError('Perfil histórico incompleto')
    return perfil


def estimar_nacional(mig: pd.DataFrame, perfil: pd.DataFrame, meses: list[int], anio: int = 2026) -> pd.DataFrame:
    """Nivel anual anclado a sep-dic 2025, sin utilizar datos nacionales de 2026."""
    base = mig[(mig.fecha.dt.year == 2025) & (mig.fecha.dt.month.isin([9,10,11,12]))].copy()
    if base.fecha.dt.month.nunique() != 4:
        raise ValueError('Falta algún mes de sep-dic 2025 para anclar el nivel')
    base['mes'] = base.fecha.dt.month
    base = base.merge(perfil,on='mes',validate='one_to_one')
    nivel = float(np.median(base.viajeros_nacionales / base.indice))
    if not np.isfinite(nivel) or nivel <= 0:
        raise ValueError('Nivel nacional inválido')
    objetivo = perfil[perfil.mes.isin(meses)].copy()
    if len(objetivo) != len(set(meses)):
        raise ValueError('Meses objetivo no cubiertos por el perfil')
    objetivo['fecha'] = pd.to_datetime(dict(year=anio,month=objetivo.mes,day=1))
    objetivo['migracion_nacional_estimada'] = nivel * objetivo.indice
    return objetivo[['fecha','migracion_nacional_estimada']].sort_values('fecha').reset_index(drop=True)


def estimar_destino(mov: pd.DataFrame, mig: pd.DataFrame, nacional: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Factor de reparto: mediana de visitantes / migración nacional por grupo."""
    obs = mov[(mov.fecha.dt.year == 2025) & (mov.fecha.dt.month.isin([9,10,11,12]))].copy()
    nat = mig[['fecha','viajeros_nacionales']]
    obs = obs.merge(nat,on='fecha',validate='many_to_one')
    if (obs.viajeros_nacionales <= 0).any():
        raise ValueError('Migración nacional de calibración debe ser positiva')
    obs['factor_mensual'] = obs.visitantes / obs.viajeros_nacionales
    factores = (obs.groupby(['subdestino','segmento'],as_index=False)
                .agg(factor_reparto=('factor_mensual','median'),meses_calibracion=('fecha','nunique')))
    if (factores.meses_calibracion < 4).any():
        raise ValueError('Se requieren cuatro meses observados por polígono/segmento')
    factores['key'] = 1
    nacional = nacional.copy()
    nacional['key'] = 1
    pred = factores.merge(nacional,on='key').drop(columns='key')
    pred['visitantes_estimados'] = pred.factor_reparto * pred.migracion_nacional_estimada
    pred['tipo_dato'] = 'Estimación'
    pred['metodo'] = 'Perfil histórico nacional + factor mediano sep-dic 2025'
    pred = pred[['fecha','subdestino','segmento','visitantes_estimados','tipo_dato','metodo','factor_reparto','meses_calibracion','migracion_nacional_estimada']]
    return pred.sort_values(['fecha','subdestino','segmento']).reset_index(drop=True), factores.drop(columns='key')


def validar_retroactivo(mov: pd.DataFrame, mig: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Leave-one-month-out en sep-dic 2025. No usa el mes evaluado para calibrar."""
    obs = mov[(mov.fecha.dt.year == 2025) & (mov.fecha.dt.month.isin([9,10,11,12]))].merge(
        mig[['fecha','viajeros_nacionales']],on='fecha',validate='many_to_one')
    filas = []
    for (sub,seg), g in obs.groupby(['subdestino','segmento']):
        if g.fecha.dt.month.nunique() != 4 or (g.viajeros_nacionales <= 0).any():
            raise ValueError(f'Calibración insuficiente: {sub}, {seg}')
        for _, fila in g.iterrows():
            train = g[g.fecha != fila.fecha]
            factor = np.median(train.visitantes / train.viajeros_nacionales)
            estimado = float(factor * fila.viajeros_nacionales)
            filas.append({'fecha':fila.fecha,'subdestino':sub,'segmento':seg,
                          'observado':float(fila.visitantes),'estimado':estimado,
                          'error':estimado-float(fila.visitantes)})
    detalle = pd.DataFrame(filas).sort_values(['fecha','subdestino','segmento']).reset_index(drop=True)
    resumen = (detalle.groupby(['subdestino','segmento'],as_index=False)
               .agg(MAE=('error',lambda x:float(np.mean(np.abs(x)))),
                    RMSE=('error',lambda x:float(np.sqrt(np.mean(np.square(x))))),
                    meses_evaluados=('fecha','nunique')))
    return detalle,resumen


def ejecutar(directorio: Path = PROCESSED, salida: Path = OUT) -> dict[str,pd.DataFrame]:
    mov,mig = cargar(directorio)
    perfil = perfil_historico(mig)
    nacional = estimar_nacional(mig,perfil,[1,2])
    pred,factores = estimar_destino(mov,mig,nacional)
    validacion,metricas = validar_retroactivo(mov,mig)
    salidas = {'perfil_estacional_nacional.csv':perfil,
               'migracion_nacional_estimada_2026.csv':nacional,
               'factores_reparto.csv':factores,
               'prediccion_peten_ene_feb_2026.csv':pred,
               'validacion_retroactiva.csv':validacion,
               'metricas_prediccion.csv':metricas}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,df in salidas.items():
        df.to_csv(salida/nombre,index=False,encoding='utf-8-sig',date_format='%Y-%m-%d')
        print(f'{nombre}: {len(df)} filas')
    return salidas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--processed',type=Path,default=PROCESSED)
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args()
    ejecutar(args.processed,args.out)

if __name__ == '__main__':
    main()
