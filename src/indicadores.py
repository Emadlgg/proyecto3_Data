"""Indicadores reproducibles de Petén a partir de data/processed.

Ejecutar: python -m src.indicadores
No altera archivos originales ni suma polígonos solapados.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROCESSED = BASE / 'data' / 'processed'
OUTPUTS = {
    'visitantes_subdestino.csv': 'visitantes_subdestino',
    'estadia_ponderada.csv': 'estadia_ponderada',
    'segmentacion_visitantes.csv': 'segmentacion_visitantes',
    'tikal_indicadores.csv': 'tikal_indicadores',
    'aimm_pasajeros_indicadores.csv': 'aimm_pasajeros_indicadores',
    'aimm_operaciones_indicadores.csv': 'aimm_operaciones_indicadores',
    'ocupacion_indicadores.csv': 'ocupacion_indicadores',
    'capacidad_hotelera.csv': 'capacidad_hotelera',
    'comparacion_fuentes_indices.csv': 'comparacion_fuentes_indices',
}

def cargar(data_dir: Path = PROCESSED) -> dict[str, pd.DataFrame]:
    names = ['movilidad_mensual_peten', 'tikal_mensual', 'aimm_pasajeros_mensual',
             'aimm_operaciones_mensual', 'ocupacion_peten', 'oferta_hotelera_peten',
             'comparacion_fuentes_peten']
    tables = {}
    for name in names:
        path = data_dir / f'{name}.csv'
        if not path.is_file():
            raise FileNotFoundError(f'Falta {path}. Ejecuta primero python -m src.etl')
        tables[name] = pd.read_csv(path, parse_dates=['fecha'] if name != 'oferta_hotelera_peten' else None)
    return tables

def indicadores(tablas: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    mov = tablas['movilidad_mensual_peten'].copy()
    mov[['visitantes', 'dias_persona']] = mov[['visitantes', 'dias_persona']].apply(pd.to_numeric, errors='raise')
    if mov[['visitantes','dias_persona']].isna().any().any() or (mov[['visitantes','dias_persona']] < 0).any().any():
        raise ValueError('Movilidad: valores ausentes o negativos')
    if (mov['dias_persona'] + 1e-7 < mov['visitantes']).any():
        raise ValueError('Movilidad: días-persona menores que visitantes')
    # Un registro por mes/subdestino/segmento; no se suman subdestinos entre sí.
    group = ['fecha', 'subdestino']
    visitantes = mov.groupby(group, as_index=False)[['visitantes','dias_persona']].sum()
    visitantes['alcance'] = 'Polígono individual; no sumar entre subdestinos'

    pernocta = mov[mov['segmento'].eq('mayor a 1 dia')].groupby(group, as_index=False)[['visitantes','dias_persona']].sum()
    pernocta['estadia_media_ponderada_dias'] = pernocta['dias_persona'].div(pernocta['visitantes'].where(pernocta['visitantes'] > 0))
    pernocta['alcance'] = 'Solo visitantes con pernocta (>1 día)'

    seg = mov.pivot_table(index=group, columns='segmento', values='visitantes', aggfunc='sum', fill_value=0).reset_index()
    seg.columns.name = None
    for c in ['mayor a 1 dia','menor a 1 dia']:
        if c not in seg: seg[c] = 0.0
    seg = seg.rename(columns={'mayor a 1 dia':'turistas_pernocta', 'menor a 1 dia':'excursionistas'})
    seg['visitantes_poligono'] = seg['turistas_pernocta'] + seg['excursionistas']
    seg['proporcion_turistas'] = seg['turistas_pernocta'].div(seg['visitantes_poligono'].where(seg['visitantes_poligono'] > 0))
    seg['proporcion_excursionistas'] = seg['excursionistas'].div(seg['visitantes_poligono'].where(seg['visitantes_poligono'] > 0))

    tik = tablas['tikal_mensual'].copy()
    tik['participacion_extranjeros'] = tik['extranjeros'].div(tik['total'].where(tik['total'] > 0))
    tik['cero_por_confirmar'] = tik['total'].eq(0)
    tik['variacion_interanual_pct'] = tik.sort_values('fecha')['total'].pct_change(12, fill_method=None).mul(100).replace([float('inf'), -float('inf')], float('nan'))

    # Pasajeros: mantener flujo y tipo separados; jamás equiparar con turistas.
    air = tablas['aimm_pasajeros_mensual'].copy()
    air['unidad'] = 'movimientos de pasajeros (no turistas únicos)'
    ops = tablas['aimm_operaciones_mensual'].copy()
    ops['unidad'] = 'operaciones aeronáuticas (no personas)'

    ocup = tablas['ocupacion_peten'].copy()
    ocup['ocupacion_pct'] = ocup['indice_ocupacion'] * 100
    if not ocup['indice_ocupacion'].between(0,1).all():
        raise ValueError('Ocupación fuera de rango [0,1]')

    oferta = tablas['oferta_hotelera_peten'].copy()
    oferta['tipo_dato'] = 'inventario al corte; no acumular trimestres'

    # Comparación de niveles en unidades distintas: índices base 100 por serie.
    cmp = tablas['comparacion_fuentes_peten'].copy().sort_values('fecha')
    campos = ['boletos_tikal','pasajeros_aimm','movilidad_poligono_aeropuerto']
    for c in campos:
        vals = pd.to_numeric(cmp[c], errors='coerce')
        primero = vals.dropna().iloc[0] if vals.notna().any() else float('nan')
        cmp[f'indice_{c}'] = vals / primero * 100 if pd.notna(primero) and primero > 0 else float('nan')
    cmp['nota'] = 'Series con universos distintos; índices relativos, no equivalencia de personas'
    return dict(visitantes_subdestino=visitantes, estadia_ponderada=pernocta,
                segmentacion_visitantes=seg, tikal_indicadores=tik,
                aimm_pasajeros_indicadores=air, aimm_operaciones_indicadores=ops,
                ocupacion_indicadores=ocup, capacidad_hotelera=oferta,
                comparacion_fuentes_indices=cmp)

def ejecutar(data_dir: Path = PROCESSED, out_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    if out_dir is None: out_dir = data_dir / 'indicadores'
    resultados = indicadores(cargar(data_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, key in OUTPUTS.items():
        resultados[key].to_csv(out_dir / filename, index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
        print(f'{filename}: {len(resultados[key])} filas')
    return resultados

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=PROCESSED)
    p.add_argument('--out', type=Path, default=None)
    args = p.parse_args()
    ejecutar(args.data, args.out)

if __name__ == '__main__':
    main()
