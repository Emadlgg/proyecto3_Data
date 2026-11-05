"""Procesamiento descriptivo de la encuesta de visitantes de Petén 2025.

No expandir resultados a población: encuesta por cuotas, sin factor de expansión.
Uso: python -m src.encuestas --input data/raw/Encuesta_visitante_Peten_2025.xlsx
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/raw/Encuesta_visitante_Peten_2025.xlsx'
OUTPUT = ROOT / 'data/processed/encuestas'
GROUPS = ['Lugar_Turistico', 'tipo_visitante']
PROFILE = {'p05': 'genero', 'p06': 'edad', 'region': 'region_residencia',
           'p08': 'pais_residencia', 'p12': 'motivo_principal',
           'p17': 'transporte_llegada', 'p35': 'uso_hospedaje',
           'p67': 'recomendacion', 'p68': 'percepcion_seguridad'}
SATISFACTION = ['T_p20', 'T_p21', 'T_p22', 'T_p23', 'T_p24', 'T_p25',
                'T_p26', 'T_p27', 'T_p28', 'T_p29', 'T_p30', 'T_p31',
                'T_p32', 'T_p33', 'T_p50', 'T_p51', 'T_p52',
                'T_p65', 'T_p66']


def leer_encuesta(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    path = Path(path)
    with pd.ExcelFile(path) as book:
        required = {'datos', 'diccionario', 'nota_metodologica'}
        if not required.issubset(book.sheet_names):
            raise ValueError(f'Faltan hojas: {sorted(required-set(book.sheet_names))}')
        data = pd.read_excel(book, sheet_name='datos')
        dictionary = pd.read_excel(book, sheet_name='diccionario')
        notes = pd.read_excel(book, sheet_name='nota_metodologica', header=None)
    if data.empty or 'SbjNum' not in data or any(c not in data for c in GROUPS):
        raise ValueError('Encuesta sin registros o identificadores/grupos obligatorios')
    if data['SbjNum'].isna().any() or data['SbjNum'].duplicated().any():
        raise ValueError('Identificadores de respuestas nulos o repetidos')
    note = ' '.join(notes.fillna('').astype(str).to_numpy().ravel()).lower()
    if 'no existe' not in note or 'no son expandibles' not in note:
        raise ValueError('No se encontró advertencia metodológica de no expansión')
    return data, dictionary, note


def porcentajes_muestra(data: pd.DataFrame, fields: dict[str, str] = PROFILE) -> pd.DataFrame:
    """Porcentajes sobre respuestas válidas DENTRO de cada subdestino y tipo.

    Los filtros del cuestionario producen no respuesta estructural: no imputar.
    """
    out = []
    for field, label in fields.items():
        if field not in data:
            continue
        for key, group in data.groupby(GROUPS, dropna=False):
            vals = group[field].astype('string').str.strip().replace('', pd.NA).dropna()
            counts = vals.value_counts(dropna=True)
            for answer, n in counts.items():
                out.append(dict(zip(GROUPS, key), indicador=label, respuesta=str(answer),
                                n_respuestas=int(n), base_valida=int(len(vals)),
                                n_encuestados=int(len(group)),
                                porcentaje_muestra=100 * n / len(vals)))
    return pd.DataFrame(out, columns=GROUPS+['indicador','respuesta','n_respuestas',
                                            'base_valida','n_encuestados','porcentaje_muestra'])


def satisfaccion_muestra(data: pd.DataFrame, dictionary: pd.DataFrame,
                         fields: list[str] = SATISFACTION) -> pd.DataFrame:
    labels = dict(zip(dictionary['columna'], dictionary['pregunta']))
    result = []
    for field in fields:
        if field not in data:
            continue
        raw = data[field]
        vals = pd.to_numeric(raw, errors='coerce')
        # Algunos archivos codifican las escalas como texto: no asumir su equivalencia.
        invalid = raw.notna() & vals.isna()
        if invalid.any():
            raise ValueError(f'{field}: escala no numérica; revisar codificación original')
        if vals.dropna().lt(1).any() or vals.dropna().gt(5).any():
            raise ValueError(f'{field}: satisfacción fuera de escala 1-5')
        for key, group in data.groupby(GROUPS, dropna=False):
            v = vals.loc[group.index].dropna()
            result.append(dict(zip(GROUPS,key), variable=field,
                               pregunta=str(labels.get(field) or field),
                               n_respuestas=int(len(v)), n_encuestados=int(len(group)),
                               media_muestra=float(v.mean()) if len(v) else None,
                               porcentaje_4_5=float(v.ge(4).mean()*100) if len(v) else None))
    return pd.DataFrame(result, columns=GROUPS+['variable','pregunta','n_respuestas',
                                           'n_encuestados','media_muestra','porcentaje_4_5'])


def cobertura_preguntas(data: pd.DataFrame, dictionary: pd.DataFrame) -> pd.DataFrame:
    d = dictionary[['columna','pregunta','% respondido']].copy()
    d = d[d['columna'].isin(data.columns)].copy()
    d['n_validas'] = d['columna'].map(data.notna().sum().to_dict()).astype(int)
    d['n_encuestados'] = len(data)
    d['porcentaje_observado'] = d['n_validas'] / len(data) * 100
    return d


def ejecutar(input_path: Path = INPUT, output: Path = OUTPUT) -> dict[str, pd.DataFrame]:
    data, dictionary, _ = leer_encuesta(input_path)
    tables = {'perfil_muestra.csv': porcentajes_muestra(data),
              'satisfaccion_muestra.csv': satisfaccion_muestra(data, dictionary),
              'cobertura_encuesta.csv': cobertura_preguntas(data, dictionary)}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for filename, df in tables.items():
        df.to_csv(output / filename, index=False, encoding='utf-8-sig')
        print(f'{filename}: {len(df)} filas')
    print(f'Encuestados en la muestra: {len(data)}; SIN expansión poblacional.')
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=INPUT)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    ejecutar(args.input, args.output)

if __name__ == '__main__':
    main()
