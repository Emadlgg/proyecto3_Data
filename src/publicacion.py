"""Publicacion atomica y restauracion de predicciones aprobadas.

Uso: python -m src.publicacion demo --root artifacts/demo_sintetica
No modifica artifacts/approved reales en el modo demo.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FILE = 'prediccion_peten_ene_feb_2026.csv'
REQUIRED = {'fecha', 'subdestino', 'segmento', 'visitantes_estimados'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False, suffix='.tmp') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp = Path(f.name)
    os.replace(tmp, path)


def verificar_predicciones(path: Path) -> dict:
    import numpy as np
    import pandas as pd
    if not path.is_file():
        raise ValueError(f'No existe archivo de predicciones: {path}')
    df = pd.read_csv(path)
    if df.empty or not REQUIRED.issubset(df.columns):
        raise ValueError('Archivo vacio o sin columnas obligatorias')
    fechas = pd.to_datetime(df['fecha'], errors='coerce', format='%Y-%m-%d')
    valores = pd.to_numeric(df['visitantes_estimados'], errors='coerce')
    if fechas.isna().any() or valores.isna().any() or not np.isfinite(valores).all() or (valores < 0).any():
        raise ValueError('Fechas o estimaciones invalidas')
    if df.duplicated(['fecha', 'subdestino', 'segmento']).any():
        raise ValueError('Claves duplicadas')
    if not ((fechas.dt.year == 2026) & fechas.dt.month.isin([1, 2])).all():
        raise ValueError('Predicciones fuera del periodo objetivo')
    if set(fechas.dt.month) != {1, 2}:
        raise ValueError('Cobertura enero-febrero incompleta')
    return {'filas': len(df), 'sha256': digest(path)}


def publicar(record: dict, archivo: Path, root: Path, *, permitir_demo: bool = False) -> dict:
    """Solo acepta estado y decision aprobados; verifica hash registrado si existe."""
    if record.get('estado') != 'CANDIDATO_ACEPTADO_NO_PUBLICADO' or record.get('decision', {}).get('aprobado') is not True:
        raise PermissionError('Candidato no aprobado: publicacion bloqueada')
    run_id = record.get('run_id', '')
    if not run_id or '/' in run_id or '\\' in run_id or run_id in {'.', '..'}:
        raise ValueError('Identificador de ejecucion invalido')
    if record.get('demo_sintetica') and not permitir_demo:
        raise PermissionError('Un candidato sintetico no puede publicarse como real')
    stats = verificar_predicciones(archivo)
    hashes = record.get('salidas', {})
    matches = [value for key, value in hashes.items() if Path(key.replace('\\', '/')).name == FILE]
    if not record.get('demo_sintetica') and (len(matches) != 1 or matches[0] != stats['sha256']):
        raise ValueError('El archivo no coincide con el hash de la ejecucion')
    approved = root / 'approved'
    version = approved / 'versions' / run_id
    if version.exists():
        raise FileExistsError('La version ya existe')
    version.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.candidate-', dir=version.parent))
    try:
        shutil.copy2(archivo, staging / FILE)
        metadata = {
            'run_id': run_id,
            'generado_utc': datetime.now(timezone.utc).isoformat(),
            'git_commit': record.get('git_commit', 'desconocido'),
            'version_procedimiento': 'lab11-v1',
            'unidad': 'visitantes estimados por subdestino, segmento y mes',
            'metrica_validacion_mae': record['decision'].get('MAE_modelo'),
            'evaluacion': record['decision'],
            'sha256': stats['sha256'],
            'demo_sintetica': bool(record.get('demo_sintetica', False)),
        }
        (staging / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(staging, version)
        _json_atomic(approved / 'current.json', {'run_id': run_id})
        return metadata
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def consultar(root: Path) -> tuple[Path, dict] | None:
    approved = root / 'approved'
    pointer = approved / 'current.json'
    if not pointer.exists():
        return None
    run_id = json.loads(pointer.read_text(encoding='utf-8'))['run_id']
    if Path(run_id).name != run_id or run_id in {'.', '..'}:
        raise ValueError('Puntero de version invalido')
    folder = approved / 'versions' / run_id
    meta = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
    path = folder / FILE
    if digest(path) != meta['sha256']:
        raise ValueError('Integridad de version aprobada comprometida')
    return path, meta


def restaurar(root: Path, run_id: str) -> dict:
    if Path(run_id).name != run_id or run_id in {'.', '..'}:
        raise ValueError('Version invalida')
    folder = root / 'approved' / 'versions' / run_id
    meta = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
    if digest(folder / FILE) != meta['sha256']:
        raise ValueError('Version alterada')
    _json_atomic(root / 'approved' / 'current.json', {'run_id': run_id})
    return meta


def demo(root: Path) -> None:
    import pandas as pd
    root.mkdir(parents=True, exist_ok=True)
    for num, value in [(1, 120), (2, 125)]:
        run_id = f'DEMO_SINTETICA_{num}'
        file = root / f'{run_id}.csv'
        pd.DataFrame([
            {'fecha': f'2026-0{m}-01', 'subdestino': 'Zona sintetica', 'segmento': 'mayor a 1 dia', 'visitantes_estimados': value + m}
            for m in (1, 2)
        ]).to_csv(file, index=False)
        record = {'run_id': run_id, 'estado': 'CANDIDATO_ACEPTADO_NO_PUBLICADO', 'decision': {'aprobado': True, 'MAE_modelo': 0}, 'demo_sintetica': True}
        publicar(record, file, root, permitir_demo=True)
    before = consultar(root)[1]['run_id']
    try:
        publicar({'run_id': 'RECHAZADO', 'estado': 'CANDIDATO_RECHAZADO_NO_PUBLICADO', 'decision': {'aprobado': False}}, root / 'DEMO_SINTETICA_2.csv', root)
    except PermissionError:
        pass
    assert consultar(root)[1]['run_id'] == before
    restored = restaurar(root, 'DEMO_SINTETICA_1')
    assert consultar(root)[1]['run_id'] == restored['run_id']
    print('DEMO OK: dos versiones sinteticas, rechazo sin sustitucion y restauracion.')
    print('Version actual:', restored['run_id'])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('accion', choices=['demo', 'estado', 'restaurar'])
    p.add_argument('--root', type=Path, default=Path('artifacts'))
    p.add_argument('--run-id')
    args = p.parse_args()
    if args.accion == 'demo':
        demo(args.root)
    elif args.accion == 'estado':
        result = consultar(args.root)
        print(json.dumps(result[1] if result else {'estado': 'SIN_VERSION_APROBADA'}, indent=2, ensure_ascii=False))
    else:
        if not args.run_id:
            p.error('--run-id es obligatorio para restaurar')
        print(restaurar(args.root, args.run_id)['run_id'])

if __name__ == '__main__':
    main()
