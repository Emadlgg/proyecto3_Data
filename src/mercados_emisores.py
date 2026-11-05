"""Mercados emisores por poligono desde la hoja Peten de movilidad mensual.

No suma poligonos, no promedia permanencias ni redistribuye factores.
Uso: python -m src.mercados_emisores
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
ORIGEN = BASE / 'data' / 'raw' / 'BD_moviidad_mensual.xlsx'
DESTINO = BASE / 'data' / 'processed' / 'indicadores' / 'mercados_emisores_peten.csv'
COLUMNAS = ['destino', 'pais', 'fecha', 'visitantes', 'es_consecutivo']


def procesar(df: pd.DataFrame) -> pd.DataFrame:
    """Consolida segmentos de un mismo pais, mes y poligono; no poligonos."""
    faltantes = set(COLUMNAS) - set(df.columns)
    if faltantes:
        raise ValueError(f'Columnas faltantes: {sorted(faltantes)}')
    d = df[COLUMNAS].copy()
    d['fecha'] = pd.to_datetime(d['fecha'], errors='coerce')
    d['visitantes'] = pd.to_numeric(d['visitantes'], errors='coerce')
    if d['fecha'].isna().any() or d['visitantes'].isna().any():
        raise ValueError('Fecha o visitantes invalidos')
    if (~d['visitantes'].ge(0)).any() or (~d['visitantes'].map(lambda x: pd.notna(x) and x != float('inf'))).any():
        raise ValueError('Visitantes negativos o infinitos')
    if d[['destino','es_consecutivo']].isna().any().any():
        raise ValueError('Destinos o segmentos faltantes')
    d['pais'] = d['pais'].astype('string').str.strip()
    d['pais'] = d['pais'].fillna('No informado').replace('', 'No informado')
    d['mercado'] = d['pais'].str.casefold().map(lambda p: 'Nacional' if p == 'guatemala' else ('No informado' if p == 'no informado' else 'Extranjero'))
    d['fecha'] = d['fecha'].dt.to_period('M').dt.to_timestamp()
    result = (d.groupby(['fecha','destino','mercado','pais'], as_index=False, dropna=False)
              .agg(visitantes=('visitantes','sum')))
    result = result.rename(columns={'destino':'subdestino'})
    return result.sort_values(['fecha','subdestino','mercado','pais']).reset_index(drop=True)


def top_mercados(df: pd.DataFrame, subdestino: str, fechas=None, limite: int = 10) -> pd.DataFrame:
    """Top de extranjeros del poligono seleccionado; sin sumar otros poligonos."""
    d = df.loc[(df['subdestino'] == subdestino) & (df['mercado'] == 'Extranjero')].copy()
    if fechas is not None:
        d = d.loc[d['fecha'].isin(pd.to_datetime(list(fechas)))]
    out = d.groupby('pais', as_index=False)['visitantes'].sum()
    return out.sort_values(['visitantes','pais'], ascending=[False,True]).head(limite).reset_index(drop=True)


def ejecutar(origen: Path = ORIGEN, salida: Path = DESTINO) -> pd.DataFrame:
    if not origen.is_file():
        raise FileNotFoundError(f'Falta {origen}')
    df = pd.read_excel(origen, sheet_name='Peten', engine='openpyxl')
    resultado = procesar(df)
    salida.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(salida, index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
    print(f'{salida}: {len(resultado)} filas; {resultado.subdestino.nunique()} poligonos')
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=ORIGEN)
    parser.add_argument('--out', type=Path, default=DESTINO)
    args = parser.parse_args()
    ejecutar(args.raw, args.out)


if __name__ == '__main__':
    main()
