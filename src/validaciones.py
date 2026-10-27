"""Auditoria no destructiva de CSV procesados del observatorio de Peten.

Uso: python -m src.validaciones
No corrige ni sobrescribe datos. El informe JSON se guarda en docs/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROCESSED = BASE / 'data' / 'processed'
FILES = {
    'movilidad_mensual_peten.csv': ('fecha', 'subdestino', 'segmento', 'visitantes', 'dias_persona', 'estadia_media_dias'),
    'movilidad_diaria_peten.csv': ('fecha', 'subdestino', 'evento', 'presencias_diarias'),
    'tikal_mensual.csv': ('fecha', 'nacionales', 'extranjeros', 'otros', 'total'),
    'aimm_pasajeros_mensual.csv': ('fecha', 'flujo', 'tipo_pasajero', 'pasajeros'),
    'aimm_operaciones_mensual.csv': ('fecha', 'tipo_operacion', 'operaciones'),
    'ocupacion_peten.csv': ('fecha', 'indice_ocupacion'),
    'oferta_hotelera_peten.csv': ('anio', 'tipo_alojamiento', 'establecimientos', 'habitaciones', 'plazas_cama'),
    'migracion_nacional_mensual.csv': ('fecha', 'viajeros_nacionales'),
    'comparacion_fuentes_peten.csv': ('fecha', 'boletos_tikal', 'pasajeros_aimm', 'movilidad_poligono_aeropuerto'),
}
NUMERIC = {
    'movilidad_mensual_peten.csv': ['visitantes', 'dias_persona'],
    'movilidad_diaria_peten.csv': ['presencias_diarias'],
    'tikal_mensual.csv': ['nacionales', 'extranjeros', 'otros', 'total'],
    'aimm_pasajeros_mensual.csv': ['pasajeros'],
    'aimm_operaciones_mensual.csv': ['operaciones'],
    'ocupacion_peten.csv': ['indice_ocupacion'],
    'oferta_hotelera_peten.csv': ['establecimientos', 'habitaciones', 'plazas_cama'],
    'migracion_nacional_mensual.csv': ['viajeros_nacionales'],
    'comparacion_fuentes_peten.csv': ['boletos_tikal', 'pasajeros_aimm', 'movilidad_poligono_aeropuerto'],
}


def evaluar(directorio: Path = PROCESSED) -> dict:
    """Devuelve hallazgos de calidad sin modificar ningun archivo de entrada."""
    reporte = {
        'directorio': str(directorio), 'archivos': {}, 'errores': [], 'advertencias': [],
        'notas_metodologicas': [
            'No sumar subdestinos de telefonia para obtener visitantes unicos de Peten.',
            'No sumar presencias diarias para calcular visitantes unicos mensuales.',
            'No interpretar pasajeros AIMM, boletos Tikal y telefonia como universos equivalentes.',
            'Enero-febrero 2026 sin cobertura telefonica no equivale a cero.',
            'Estadia media ponderada: dias-persona / visitantes, solo segmento mayor a 1 dia.',
            'No comparar directamente 2026 parcial con un ano completo.',
        ],
    }
    datos: dict[str, pd.DataFrame] = {}

    def error(msg: str) -> None:
        reporte['errores'].append(msg)

    def aviso(msg: str) -> None:
        reporte['advertencias'].append(msg)

    for nombre, requeridas in FILES.items():
        archivo = directorio / nombre
        if not archivo.is_file():
            error(f'{nombre}: archivo ausente')
            continue
        try:
            df = pd.read_csv(archivo)
        except Exception as exc:
            error(f'{nombre}: no se pudo leer: {exc}')
            continue
        if df.empty:
            error(f'{nombre}: vacio')
            continue
        faltan = sorted(set(requeridas) - set(df.columns))
        if faltan:
            error(f'{nombre}: columnas ausentes: {faltan}')
            continue
        datos[nombre] = df
        info = {
            'filas': int(len(df)), 'columnas': list(df.columns),
            'duplicados_exactos': int(df.duplicated().sum()),
            'nulos_por_columna': {k: int(v) for k, v in df.isna().sum().items()},
        }
        if 'fecha' in df.columns:
            fechas = pd.to_datetime(df['fecha'], errors='coerce')
            info['fechas_invalidas'] = int(fechas.isna().sum())
            if fechas.notna().any():
                info['fecha_min'] = str(fechas.min().date())
                info['fecha_max'] = str(fechas.max().date())
            if fechas.isna().any():
                error(f'{nombre}: fechas invalidas')
        if info['duplicados_exactos']:
            aviso(f'{nombre}: {info["duplicados_exactos"]} duplicados exactos')
        for col in NUMERIC[nombre]:
            vals = pd.to_numeric(df[col], errors='coerce')
            if vals.isna().any():
                error(f'{nombre}: {col} contiene valores vacios/no numericos')
            if vals.lt(0).any():
                error(f'{nombre}: {col} contiene valores negativos')
        reporte['archivos'][nombre] = info

    mov = datos.get('movilidad_mensual_peten.csv')
    if mov is not None:
        s = mov['segmento'].astype(str).str.lower().str.strip()
        # El ETL utiliza el literal normalizado 'mayor a 1 dia'.
        es_pernocta = s.eq('mayor a 1 dia')
        visitantes = pd.to_numeric(mov['visitantes'], errors='coerce')
        dias_persona = pd.to_numeric(mov['dias_persona'], errors='coerce')
        estadia = pd.to_numeric(mov['estadia_media_dias'], errors='coerce')
        aplica = es_pernocta & visitantes.gt(0)

        if not es_pernocta.any():
            aviso('Movilidad: no se encontro segmento mayor a 1 dia')
        segmentos_desconocidos = ~s.isin(['mayor a 1 dia', 'menor a 1 dia'])
        if segmentos_desconocidos.any():
            error('Movilidad: segmentos desconocidos')
        if estadia[aplica].isna().any():
            error('Movilidad: falta estadia media en registros con pernocta y visitantes positivos')
        if estadia.dropna().lt(0).any():
            error('Movilidad: estadia media negativa')
        esperado = dias_persona[aplica] / visitantes[aplica]
        diferencia = (esperado - estadia[aplica]).abs()
        if diferencia.gt(1e-5).any():
            error('Movilidad: estadia media no coincide con dias-persona/visitantes')
        if estadia[~aplica].notna().any():
            aviso('Movilidad: hay valores de estadia media donde no aplica')
        if dias_persona.lt(visitantes - 1e-7).any():
            error('Movilidad: dias-persona menores que visitantes')
        fechas = pd.to_datetime(mov['fecha'], errors='coerce')
        if fechas.dt.to_period('M').nunique() != 10:
            aviso('Movilidad mensual: cobertura distinta de 10 meses; revisar')
        if ((fechas.dt.year == 2026) & fechas.dt.month.isin([1, 2])).any():
            aviso('Movilidad: existen registros ene-feb 2026; verificar si son estimaciones')
        if mov.duplicated(['fecha', 'subdestino', 'segmento']).any():
            error('Movilidad: claves fecha-subdestino-segmento repetidas')

    tik = datos.get('tikal_mensual.csv')
    if tik is not None:
        componentes = tik[['nacionales', 'extranjeros', 'otros']].apply(pd.to_numeric, errors='coerce')
        total = pd.to_numeric(tik['total'], errors='coerce')
        diferencia = componentes.sum(axis=1, min_count=3) - total
        if diferencia.abs().gt(1e-5).any():
            error('Tikal: total diferente de suma de categorias')
        ceros = tik.loc[total.eq(0), 'fecha'].astype(str).tolist()
        reporte['ceros_tikal'] = ceros
        if ceros:
            aviso(f'Tikal: {len(ceros)} meses con cero; confirmar cierre o ausencia de datos')
        if tik.duplicated(['fecha']).any():
            error('Tikal: fecha mensual repetida')

    occ = datos.get('ocupacion_peten.csv')
    if occ is not None:
        vals = pd.to_numeric(occ['indice_ocupacion'], errors='coerce')
        if vals.gt(1).any():
            aviso('Ocupacion: hay valores mayores que 1; verificar si la unidad es porcentaje 0-100')
        if vals.gt(100).any():
            error('Ocupacion: valor superior a 100')
        if occ.duplicated(['fecha']).any():
            error('Ocupacion: mes duplicado')

    oferta = datos.get('oferta_hotelera_peten.csv')
    if oferta is not None and 'trimestre' in oferta.columns:
        aviso('Oferta hotelera: interpretar cortes como inventario, no sumar trimestres ni anualizar 2026 parcial')

    cmp = datos.get('comparacion_fuentes_peten.csv')
    if cmp is not None:
        if cmp.duplicated(['fecha']).any():
            error('Comparacion: meses repetidos')
        reporte['meses_comparacion'] = cmp['fecha'].astype(str).tolist()
        if len(cmp) < 4:
            aviso('Comparacion: menos de cuatro meses coincidentes')
    return reporte


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=PROCESSED)
    parser.add_argument('--out', type=Path, default=BASE / 'docs' / 'reporte_validacion.json')
    args = parser.parse_args()
    reporte = evaluar(args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Archivos evaluados: {len(reporte['archivos'])}/{len(FILES)}")
    print(f"Errores: {len(reporte['errores'])} | Advertencias: {len(reporte['advertencias'])}")
    for item in reporte['errores']:
        print('ERROR:', item)
    for item in reporte['advertencias']:
        print('AVISO:', item)
    print('Reporte:', args.out)
    return 1 if reporte['errores'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
