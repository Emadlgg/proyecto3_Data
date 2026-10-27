"""ETL reproducible del observatorio de Tikal y Flores (Petén).

Ejecutar desde la raíz del repositorio: python -m src.etl
Las bases originales nunca se sobrescriben. No publica microdatos.
"""
from __future__ import annotations

import argparse
import logging
import unicodedata
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

LOG = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw'
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'


def normalizar(texto: object) -> str:
    if pd.isna(texto):
        return ''
    texto = unicodedata.normalize('NFKD', str(texto).strip())
    return ''.join(c for c in texto if not unicodedata.combining(c)).casefold()


def encontrar(raw: Path, *nombres: str) -> Path:
    for nombre in nombres:
        p = raw / nombre
        if p.is_file():
            return p
    raise FileNotFoundError(f'No se encontró ninguno de {nombres} en {raw}.')


def leer_hoja_movilidad(archivo: Path, hoja: str = 'Peten') -> pd.DataFrame:
    """Corrige en memoria el problema de dimension A1 de estos libros."""
    wb = load_workbook(archivo, read_only=True, data_only=True)
    try:
        ws = wb[hoja]
        ws.reset_dimensions()
        filas = ws.values
        columnas = next(filas)
        df = pd.DataFrame(filas, columns=columnas)
    finally:
        wb.close()
    df.columns = [str(c).strip() for c in df.columns]
    return df.dropna(how='all').reset_index(drop=True)


def verificar_columnas(df: pd.DataFrame, requeridas: set[str], fuente: str) -> None:
    faltan = requeridas - set(df.columns)
    if faltan:
        raise ValueError(f'{fuente}: faltan columnas {sorted(faltan)}')


def verificar_no_negativos(df: pd.DataFrame, columnas: list[str], fuente: str) -> None:
    for col in columnas:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].isna().any():
            raise ValueError(f'{fuente}: hay valores ausentes/no numéricos en {col}')
        if (df[col] < 0).any():
            raise ValueError(f'{fuente}: valores negativos en {col}')


def fechas_por_anio_mes(df: pd.DataFrame, anio: str, mes: str) -> pd.Series:
    fechas = pd.to_datetime(dict(year=pd.to_numeric(df[anio]), month=pd.to_numeric(df[mes]), day=1), errors='coerce')
    if fechas.isna().any():
        raise ValueError(f'Fechas inválidas en {anio}/{mes}')
    return fechas


def movilidad_mensual(raw: Path) -> pd.DataFrame:
    archivo = encontrar(raw, 'BD_moviidad_mensual.xlsx', 'BD_movilidad_mensual.xlsx')
    df = leer_hoja_movilidad(archivo)
    verificar_columnas(df, {'destino','sub_grupo','anio','mes','pais','es_consecutivo','fecha','visitantes','dias_persona'}, archivo.name)
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    if df.fecha.isna().any():
        raise ValueError('Movilidad mensual: fechas inválidas')
    verificar_no_negativos(df, ['visitantes','dias_persona'], archivo.name)
    df['segmento'] = df.es_consecutivo.map(normalizar)
    if not df.segmento.isin({'mayor a 1 dia', 'menor a 1 dia'}).all():
        raise ValueError('Movilidad mensual: segmentos desconocidos')
    if (df.dias_persona < df.visitantes).any():
        raise ValueError('Movilidad mensual: días-persona menores que visitantes')
    df['subdestino'] = df.destino.astype('string').str.strip().str.title()
    df['pais'] = df.pais.fillna('Sin dato')
    # Agregación SOLO dentro del mismo subdestino, mes y segmento.
    result = (df.groupby(['fecha','subdestino','segmento'], as_index=False, dropna=False)
              [['visitantes','dias_persona']].sum())
    result['estadia_media_dias'] = pd.NA
    m = result.segmento.eq('mayor a 1 dia') & result.visitantes.gt(0)
    result.loc[m, 'estadia_media_dias'] = result.loc[m, 'dias_persona'] / result.loc[m, 'visitantes']
    # No sumar subdestinos: representan polígonos que se pueden solapar.
    return result.sort_values(['fecha','subdestino','segmento']).reset_index(drop=True)


def movilidad_diaria(raw: Path) -> pd.DataFrame:
    archivo = encontrar(raw, 'BD_moviidad_diario.xlsx', 'BD_movilidad_diario.xlsx')
    df = leer_hoja_movilidad(archivo)
    verificar_columnas(df, {'destino','idfecha','evento','cantidad_visitantes'}, archivo.name)
    df['fecha'] = pd.to_datetime(df.idfecha, errors='coerce')
    if df.fecha.isna().any():
        raise ValueError('Movilidad diaria: fechas inválidas')
    verificar_no_negativos(df, ['cantidad_visitantes'], archivo.name)
    df['subdestino'] = df.destino.astype('string').str.strip().str.title()
    df['evento'] = df.evento.fillna('Sin clasificar').astype(str).str.strip()
    # Presencia diaria, NO visitantes únicos mensuales.
    result = (df.groupby(['fecha','subdestino','evento'], as_index=False)
              .cantidad_visitantes.sum().rename(columns={'cantidad_visitantes':'presencias_diarias'}))
    return result.sort_values(['fecha','subdestino','evento']).reset_index(drop=True)


def tikal(raw: Path) -> pd.DataFrame:
    df = pd.read_excel(encontrar(raw, 'Visitantes_Tikal_2017-2026.xlsx'), sheet_name='Datos')
    df.columns = df.columns.str.strip()
    verificar_columnas(df, {'año','mes','nacionales','extranjeros','otros','total'}, 'Tikal')
    meses = {normalizar(m):i for i,m in enumerate(['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'],1)}
    df['mes_num'] = df.mes.map(lambda x: meses.get(normalizar(x)))
    if df.mes_num.isna().any():
        raise ValueError('Tikal: mes desconocido')
    df['fecha'] = fechas_por_anio_mes(df, 'año', 'mes_num')
    verificar_no_negativos(df, ['nacionales','extranjeros','otros','total'], 'Tikal')
    if not (df[['nacionales','extranjeros','otros']].sum(axis=1).eq(df.total)).all():
        raise ValueError('Tikal: el total no coincide con sus componentes')
    result = df[['fecha','nacionales','extranjeros','otros','total']].copy()
    result['advertencia_cero'] = result.total.eq(0)
    if result.fecha.duplicated().any():
        raise ValueError('Tikal: fechas duplicadas')
    return result.sort_values('fecha').reset_index(drop=True)


def aimm_pasajeros(raw: Path) -> pd.DataFrame:
    # Fuente consolidada 2022/2024/2025: incluye doméstico, internacional y privado.
    consolidado = pd.read_excel(encontrar(raw,'AIMM_Consolidado_2022-2025.xlsx'),sheet_name='Base Consolidada',header=2)
    verificar_columnas(consolidado, {'Año','N° Mes','Tipo de Flujo','Tipo de Pasajero','Pasajeros'}, 'AIMM consolidado')
    verificar_no_negativos(consolidado,['Pasajeros'],'AIMM consolidado')
    consolidado['fecha'] = fechas_por_anio_mes(consolidado,'Año','N° Mes')
    base = (consolidado.groupby(['fecha','Tipo de Flujo','Tipo de Pasajero'],as_index=False)['Pasajeros'].sum()
            .rename(columns={'Tipo de Flujo':'flujo','Tipo de Pasajero':'tipo_pasajero','Pasajeros':'pasajeros'}))
    base['fuente'] = 'consolidado'
    # Aerolíneas cubre 2023 y ene-abr 2026. No se suman ambas fuentes.
    aerolineas = pd.read_excel(encontrar(raw,'AIMM_Aerolineas_2023-2026.xlsx'),sheet_name='Base de Datos')
    verificar_columnas(aerolineas, {'Año','mes_numero','Tipo de Flujo','Pasajeros'}, 'AIMM aerolíneas')
    verificar_no_negativos(aerolineas,['Pasajeros'],'AIMM aerolíneas')
    aerolineas['fecha'] = fechas_por_anio_mes(aerolineas,'Año','mes_numero')
    a = (aerolineas.groupby(['fecha','Tipo de Flujo'],as_index=False)['Pasajeros'].sum()
         .rename(columns={'Tipo de Flujo':'flujo','Pasajeros':'pasajeros'}))
    a['tipo_pasajero'] = 'No desagregado'
    a['fuente'] = 'aerolineas'
    # Solo meses que no existen en el consolidado, evitando doble conteo.
    a = a[~a.fecha.isin(base.fecha.unique())]
    return pd.concat([base,a],ignore_index=True).sort_values(['fecha','flujo','tipo_pasajero']).reset_index(drop=True)


def aimm_operaciones(raw: Path) -> pd.DataFrame:
    df = pd.read_excel(encontrar(raw,'AIMM_Operaciones_Aeronauticas_2022-2026.xlsx'),sheet_name='Base de Operaciones',header=2)
    verificar_columnas(df, {'Año','N° Mes','Tipo de Operación','Operaciones'}, 'AIMM operaciones')
    verificar_no_negativos(df,['Operaciones'],'AIMM operaciones')
    df['fecha'] = fechas_por_anio_mes(df,'Año','N° Mes')
    result = (df.groupby(['fecha','Tipo de Operación'],as_index=False)['Operaciones'].sum()
              .rename(columns={'Tipo de Operación':'tipo_operacion','Operaciones':'operaciones'}))
    return result.sort_values(['fecha','tipo_operacion']).reset_index(drop=True)


def hoteleria(raw: Path) -> tuple[pd.DataFrame,pd.DataFrame]:
    ocup = pd.read_csv(encontrar(raw,'indice_ocupacion_mensual_2023_2025_1.csv'))
    verificar_columnas(ocup,{'anio','mes','departamento','indice_ocupacion'},'Ocupación')
    ocup = ocup[ocup.departamento.map(normalizar).eq('peten')].copy()
    ocup['fecha'] = fechas_por_anio_mes(ocup,'anio','mes')
    ocup['indice_ocupacion'] = pd.to_numeric(ocup.indice_ocupacion,errors='coerce')
    if ocup.indice_ocupacion.isna().any() or not ocup.indice_ocupacion.between(0,1).all():
        raise ValueError('Ocupación: valores fuera de [0,1]')
    if ocup.fecha.duplicated().any():
        raise ValueError('Ocupación: meses duplicados')
    oferta = pd.read_csv(encontrar(raw,'oferta_hotelera_2022_2026.csv'))
    verificar_columnas(oferta,{'anio','trimestre','departamento','tipo_alojamiento','establecimientos','habitaciones','plazas_cama'},'Oferta')
    oferta = oferta[oferta.departamento.map(normalizar).eq('peten')].copy()
    verificar_no_negativos(oferta,['establecimientos','habitaciones','plazas_cama'],'Oferta')
    # Mantener año, trimestre y tipo; no interpretar inventarios como flujos mensuales.
    return (ocup[['fecha','indice_ocupacion']].sort_values('fecha').reset_index(drop=True),
            oferta[['anio','trimestre','tipo_alojamiento','establecimientos','habitaciones','plazas_cama']].sort_values(['anio','trimestre','tipo_alojamiento']).reset_index(drop=True))


def migracion(raw: Path) -> pd.DataFrame:
    archivo = encontrar(raw,'Base_Migracion_2009-2026jun.xlsx')
    df = pd.read_excel(archivo,sheet_name='Datos',usecols=['Año','Mes cod','Viajero'])
    verificar_no_negativos(df,['Viajero'],'Migración')
    df['fecha'] = fechas_por_anio_mes(df,'Año','Mes cod')
    # Registros nacionales: suma de viajeros (NO visitantes únicos de Petén).
    return (df.groupby('fecha',as_index=False).Viajero.sum()
            .rename(columns={'Viajero':'viajeros_nacionales'}).sort_values('fecha').reset_index(drop=True))


def comparacion_fuentes(mov: pd.DataFrame,tik: pd.DataFrame,air: pd.DataFrame) -> pd.DataFrame:
    # Usar una sola serie por subdestino, sin sumar los polígonos.
    mov_air = mov[mov.subdestino.map(normalizar).eq('mundo maya aeropuerto')]
    mov_air = mov_air.groupby('fecha',as_index=False).visitantes.sum().rename(columns={'visitantes':'movilidad_poligono_aeropuerto'})
    t = tik[['fecha','total']].rename(columns={'total':'boletos_tikal'})
    a = air.groupby('fecha',as_index=False).pasajeros.sum().rename(columns={'pasajeros':'pasajeros_aimm'})
    joined = t.merge(a,on='fecha',how='inner').merge(mov_air,on='fecha',how='inner')
    # Las unidades y poblaciones son diferentes. No sumarlas ni restarlas para inferir turistas.
    return joined.sort_values('fecha').reset_index(drop=True)


def ejecutar(raw: Path=RAW_DIR, processed: Path=PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    if not raw.is_dir():
        raise FileNotFoundError(f'No existe {raw}; coloca allí los originales')
    processed.mkdir(parents=True,exist_ok=True)
    LOG.info('Leyendo movilidad...')
    mensual = movilidad_mensual(raw)
    diaria = movilidad_diaria(raw)
    tik = tikal(raw)
    air = aimm_pasajeros(raw)
    ops = aimm_operaciones(raw)
    ocup,oferta = hoteleria(raw)
    mig = migracion(raw)
    comparacion = comparacion_fuentes(mensual,tik,air)
    salidas = {
        'movilidad_mensual_peten.csv':mensual,
        'movilidad_diaria_peten.csv':diaria,
        'tikal_mensual.csv':tik,
        'aimm_pasajeros_mensual.csv':air,
        'aimm_operaciones_mensual.csv':ops,
        'ocupacion_peten.csv':ocup,
        'oferta_hotelera_peten.csv':oferta,
        'migracion_nacional_mensual.csv':mig,
        'comparacion_fuentes_peten.csv':comparacion,
    }
    for nombre,df in salidas.items():
        ruta = processed/nombre
        df.to_csv(ruta,index=False,encoding='utf-8-sig',date_format='%Y-%m-%d')
        LOG.info('%-38s %6d filas',nombre,len(df))
    return salidas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,default=RAW_DIR)
    parser.add_argument('--processed',type=Path,default=PROCESSED_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    ejecutar(args.raw,args.processed)
    print('ETL completado. Los datos originales no fueron modificados.')


if __name__ == '__main__':
    main()
