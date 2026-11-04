"""Diagnostico retrospectivo multiventana de horizonte 2, sin publicacion.

Uso: python -m src.optimizacion_ventanas --data data/processed
No selecciona ni aprueba modelos de produccion.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

METODOS = ('persistencia', 'media_movil', 'reparto_ultimo', 'reparto_mediano')


def preparar(mov: pd.DataFrame, mig: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = mov.copy()
    n = mig.copy()
    for df in (m, n):
        df['fecha'] = pd.to_datetime(df['fecha'], errors='raise').dt.to_period('M').dt.to_timestamp()
    req_m = {'fecha', 'subdestino', 'segmento', 'visitantes'}
    req_n = {'fecha', 'viajeros_nacionales'}
    if not req_m.issubset(m.columns) or not req_n.issubset(n.columns):
        raise ValueError('Faltan columnas obligatorias')
    if m.duplicated(['fecha','subdestino','segmento']).any() or n.duplicated(['fecha']).any():
        raise ValueError('Claves mensuales duplicadas')
    for df, col in ((m,'visitantes'),(n,'viajeros_nacionales')):
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if not np.isfinite(df[col].to_numpy(dtype=float)).all() or df[col].lt(0).any():
            raise ValueError(f'{col} contiene valores invalidos')
    return m.sort_values('fecha'), n.sort_values('fecha')


def ventanas_validas(mov: pd.DataFrame, minimo_historia: int = 2) -> pd.DataFrame:
    """Origenes con 2 meses siguientes observados para TODOS los grupos.

    La historia de cada grupo debe ser consecutiva hasta el origen; los saltos
    invalidan la historia y no se imputan meses ausentes.
    """
    if minimo_historia < 2:
        raise ValueError('minimo_historia debe ser >= 2')
    grupos = mov[['subdestino','segmento']].drop_duplicates()
    ng = len(grupos)
    if not ng:
        return pd.DataFrame(columns=['origen','mes_1','mes_2','grupos'])
    conteos = mov.groupby('fecha').size()
    completas = set(conteos[conteos.eq(ng)].index)
    salida = []
    for origen in sorted(completas):
        meses = pd.date_range(end=origen, periods=minimo_historia, freq='MS')
        futuro = pd.date_range(start=origen + pd.DateOffset(months=1), periods=2, freq='MS')
        if all(x in completas for x in list(meses)+list(futuro)):
            salida.append({'origen': origen, 'mes_1': futuro[0], 'mes_2': futuro[1], 'grupos': ng})
    return pd.DataFrame(salida, columns=['origen','mes_1','mes_2','grupos'])


def _pronosticos(hist: pd.DataFrame, nat_hist: pd.DataFrame, nat_future: pd.DataFrame, origen: pd.Timestamp) -> dict:
    """Pronosticos construidos solo con historia previa al origen.

    Reparto utiliza valores nacionales del horizonte como escenario ex-post;
    NO equivale a pronostico operativo si esos valores no eran conocidos.
    """
    h = hist.sort_values('fecha')
    ult = float(h['visitantes'].iloc[-1])
    media = float(h['visitantes'].tail(3).mean())
    merged = h.merge(nat_hist[['fecha','viajeros_nacionales']], on='fecha', how='left')
    valid = merged['viajeros_nacionales'].gt(0) & merged['viajeros_nacionales'].notna()
    factores = (merged.loc[valid,'visitantes'] / merged.loc[valid,'viajeros_nacionales']).to_numpy()
    res = {'persistencia':[ult,ult], 'media_movil':[media,media]}
    if len(factores) and len(nat_future) == 2 and nat_future['viajeros_nacionales'].gt(0).all():
        national = nat_future['viajeros_nacionales'].to_numpy(dtype=float)
        res['reparto_ultimo'] = list(float(factores[-1]) * national)
        res['reparto_mediano'] = list(float(np.median(factores)) * national)
    return res


def evaluar_ventanas(mov: pd.DataFrame, mig: pd.DataFrame, minimo_historia: int = 2) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    mov, mig = preparar(mov, mig)
    ventanas = ventanas_validas(mov, minimo_historia)
    detalles = []
    grupos = mov[['subdestino','segmento']].drop_duplicates().itertuples(index=False, name=None)
    for origen, mes1, mes2, _ in ventanas.itertuples(index=False, name=None):
        future_nat = mig[mig.fecha.isin([mes1,mes2])].sort_values('fecha')
        for sub, seg in mov[['subdestino','segmento']].drop_duplicates().itertuples(index=False, name=None):
            serie = mov[(mov.subdestino == sub)&(mov.segmento == seg)].sort_values('fecha')
            hist = serie[serie.fecha <= origen]
            fut = serie[serie.fecha.isin([mes1,mes2])].sort_values('fecha')
            if len(fut) != 2:
                continue
            preds = _pronosticos(hist, mig[mig.fecha <= origen], future_nat, origen)
            for metodo, valores in preds.items():
                for horizonte, (fecha, y, yhat) in enumerate(zip(fut.fecha, fut.visitantes, valores), start=1):
                    detalles.append({'origen':origen,'fecha':fecha,'horizonte':horizonte,
                        'subdestino':sub,'segmento':seg,'metodo':metodo,
                        'observado':float(y),'estimado':float(yhat),
                        'error':float(yhat-y),'error_absoluto':abs(float(yhat-y)),
                        'informacion_nacional_futura':metodo.startswith('reparto_')})
    d = pd.DataFrame(detalles, columns=['origen','fecha','horizonte','subdestino','segmento','metodo','observado','estimado','error','error_absoluto','informacion_nacional_futura'])
    if d.empty:
        resumen = pd.DataFrame(columns=['metodo','n','ventanas','MAE','RMSE','requiere_nacional_futura'])
    else:
        resumen = d.groupby('metodo',as_index=False).agg(n=('error','size'),ventanas=('origen','nunique'),
            MAE=('error_absoluto','mean'), MSE=('error',lambda s: float(np.mean(np.square(s)))),
            requiere_nacional_futura=('informacion_nacional_futura','max'))
        resumen['RMSE'] = np.sqrt(resumen.pop('MSE'))
        resumen = resumen.sort_values('MAE').reset_index(drop=True)
    return ventanas, d, resumen



def comparacion_justa(detalle: pd.DataFrame, metodos: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Comparar métodos exclusivamente sobre las mismas unidades de evaluación.

    Una unidad es origen, fecha, horizonte, subdestino y segmento. No permite
    duplicados ni emparejar predicciones de distintos cortes temporales.
    """
    cols = ['origen', 'fecha', 'horizonte', 'subdestino', 'segmento']
    output_cols = ['metodo', 'n', 'ventanas', 'MAE', 'RMSE', 'requiere_nacional_futura']
    if not metodos or len(set(metodos)) != len(metodos):
        raise ValueError('La lista de métodos debe ser única y no vacía')
    required = set(cols + ['metodo', 'observado', 'estimado', 'informacion_nacional_futura'])
    if not required.issubset(detalle.columns):
        raise ValueError('Faltan columnas de evaluación')
    d = detalle.loc[detalle['metodo'].isin(metodos)].copy()
    if d.duplicated(cols + ['metodo']).any():
        raise ValueError('Hay predicciones duplicadas para la misma unidad')
    if d.empty or not set(metodos).issubset(set(d.metodo)):
        return pd.DataFrame(columns=cols + ['metodo','observado','estimado','error','error_absoluto','informacion_nacional_futura']), pd.DataFrame(columns=output_cols)
    d['observado'] = pd.to_numeric(d['observado'], errors='coerce')
    d['estimado'] = pd.to_numeric(d['estimado'], errors='coerce')
    if not np.isfinite(d[['observado','estimado']].to_numpy(dtype=float)).all():
        raise ValueError('Observados o estimados no finitos')
    # Intersección estricta: cada unidad debe estar presente en todos los métodos.
    presentes = d.groupby(cols, dropna=False)['metodo'].nunique()
    claves = presentes[presentes.eq(len(metodos))].index
    if len(claves) == 0:
        return d.iloc[0:0], pd.DataFrame(columns=output_cols)
    selected = d.set_index(cols).loc[claves].reset_index()
    # Una misma unidad debe conservar exactamente el mismo valor observado.
    if selected.groupby(cols, dropna=False)['observado'].nunique().gt(1).any():
        raise ValueError('Valores observados inconsistentes entre métodos')
    selected['error'] = selected['estimado'] - selected['observado']
    selected['error_absoluto'] = selected['error'].abs()
    rows = []
    for metodo, group in selected.groupby('metodo'):
        rows.append({'metodo':metodo, 'n':len(group), 'ventanas':group['origen'].nunique(),
                     'MAE':float(group.error_absoluto.mean()),
                     'RMSE':float(np.sqrt(np.mean(np.square(group.error)))),
                     'requiere_nacional_futura':bool(group.informacion_nacional_futura.any())})
    return selected.sort_values(cols + ['metodo']).reset_index(drop=True), pd.DataFrame(rows, columns=output_cols).sort_values('MAE').reset_index(drop=True)


def comparaciones_finales(detalle: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """Dos comparaciones: operativa y ex-post; ninguna aprueba producción."""
    return {
        'operativa': comparacion_justa(detalle, ('persistencia', 'media_movil')),
        'expost': comparacion_justa(detalle, METODOS),
    }

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=Path('data/processed'))
    p.add_argument('--out',type=Path,default=None)
    p.add_argument('--minimo-historia',type=int,default=2)
    a=p.parse_args()
    out=a.out or a.data/'optimizacion'
    mov=pd.read_csv(a.data/'movilidad_mensual_peten.csv')
    mig=pd.read_csv(a.data/'migracion_nacional_mensual.csv')
    v,d,r=evaluar_ventanas(mov,mig,a.minimo_historia)
    out.mkdir(parents=True,exist_ok=True)
    for name,df in [('ventanas_h2.csv',v),('diagnostico_multiventana_h2.csv',d),('comparacion_multiventana_h2.csv',r)]:
        df.to_csv(out/name,index=False)
        print(f'{name}: {len(df)} filas')
    print('Diagnostico retrospectivo. Los repartos usan migracion nacional futura observada (escenario ex-post).')
    print('NO publica resultados ni modifica el pipeline.')
    if not r.empty: print(r.to_string(index=False))
    for nombre, (detalle_comun, tabla) in comparaciones_finales(d).items():
        detalle_comun.to_csv(out / f'comparacion_{nombre}_detalle.csv', index=False)
        tabla.to_csv(out / f'comparacion_{nombre}_resumen.csv', index=False)
        print(f'\nComparación {nombre}: {len(detalle_comun)} predicciones emparejadas')
        if not tabla.empty: print(tabla.to_string(index=False))
    print('ATENCIÓN: la comparación ex-post no demuestra capacidad de pronóstico operativo.')

if __name__ == '__main__':
    main()
