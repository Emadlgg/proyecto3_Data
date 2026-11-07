"""Organizador conservador para proyecto3_Data (Windows/PowerShell).

Uso: python scripts/organizar_proyecto.py [--apply] [--clean-cache]
Por defecto SOLO muestra un plan. --apply mueve PDFs conocidos, nunca datos o codigo.
--clean-cache elimina exclusivamente caches regenerables, previa copia de seguridad.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVES = {
    'Avance_Lab10.pdf': 'labs/lab10/docs/Avance_Lab10.pdf',
    'Avance_Laboratorio_11.pdf': 'labs/lab11/docs/Avance_Laboratorio_11.pdf',
    'Informe_Final_Lab11.pdf': 'labs/lab11/docs/Informe_Final_Lab11.pdf',
    'avance_lab12.pdf': 'labs/lab12_powerbi/docs/avance_lab12.pdf',
    'informe_final_lab12.pdf': 'labs/lab12_powerbi/docs/informe_final_lab12.pdf',
    'docs/informe_lab10.pdf': 'labs/lab10/docs/informe_lab10.pdf',
    'docs/informe_lab10.tex': 'labs/lab10/docs/informe_lab10.tex',
}
CACHE_DIRS = {'.pytest_cache', '__pycache__', '.ipynb_checkpoints', '.mypy_cache', '.ruff_cache'}
PROTECTED = ('.git', '.venv', 'data', 'artifacts', 'mlruns', 'mlartifacts', 'src', 'pages', 'tests', 'config')

def inside(p: Path) -> bool:
    return p.resolve().is_relative_to(ROOT.resolve())

def plan():
    ops = []
    for src, dst in MOVES.items():
        s, d = ROOT / src, ROOT / dst
        if s.is_file():
            if d.exists():
                print(f'OMITIDO (destino existe): {src} -> {dst}')
            else:
                ops.append((s, d))
    return ops

def caches():
    found = []
    for p in ROOT.rglob('*'):
        if not p.is_dir() or p.name not in CACHE_DIRS:
            continue
        rel = p.relative_to(ROOT)
        if any(x in PROTECTED[:2] for x in rel.parts):
            continue
        if any(parent.name in CACHE_DIRS for parent in p.parents if inside(parent)):
            continue
        found.append(p)
    return found

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true', help='Aplicar cambios (sin esta opcion solo previsualiza)')
    ap.add_argument('--clean-cache', action='store_true', help='Respaldar y eliminar caches regenerables')
    ap.add_argument('--restore', type=Path, help='Restaurar movimientos desde un manifest.json de respaldo')
    args = ap.parse_args()
    if args.restore:
        manifest = args.restore.resolve()
        info = json.loads(manifest.read_text(encoding='utf-8'))
        for entry in reversed(info['moves']):
            old, new = ROOT / entry['source'], ROOT / entry['destination']
            if not new.exists() or old.exists():
                print('OMITIDO restauracion:', entry)
                continue
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(new), str(old))
            print('RESTAURADO:', old.relative_to(ROOT))
        print('Caches respaldadas, si las hubo, se conservan en:', manifest.parent)
        return
    ops = plan()
    cs = caches() if args.clean_cache else []
    print('Proyecto:', ROOT)
    print('Movimientos propuestos:', len(ops))
    for s, d in ops:
        print(' MOVER:', s.relative_to(ROOT), '->', d.relative_to(ROOT))
    print('Caches propuestas para limpieza:', len(cs))
    for p in cs:
        print(' CACHE:', p.relative_to(ROOT))
    print('NO SE TOCAN: datos, scripts, notebooks, pruebas, .git, MLflow, Docker, PBIX, artifacts.')
    if not args.apply:
        print('SIMULACION: no se modifico nada. Usa --apply para ejecutar.')
        return
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / '_organizacion_backup' / stamp
    backup.mkdir(parents=True, exist_ok=False)
    log = {'created': stamp, 'moves': [], 'cache_backup': []}
    try:
        for s, d in ops:
            if not inside(s) or not inside(d) or d.exists():
                raise RuntimeError(f'Ruta insegura o colision: {s} -> {d}')
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
            log['moves'].append({'source': str(s.relative_to(ROOT)), 'destination': str(d.relative_to(ROOT))})
            print('MOVIDO:', s.relative_to(ROOT), '->', d.relative_to(ROOT))
        for p in cs:
            if not p.exists():
                continue
            rel = p.relative_to(ROOT)
            dest = backup / 'cache' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            log['cache_backup'].append(str(rel))
            print('CACHE RESPALDADA:', rel)
    finally:
        (backup / 'manifest.json').write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Registro:', backup / 'manifest.json')
    print('Revisar: python -m pytest -q; git status --short')

if __name__ == '__main__':
    main()
