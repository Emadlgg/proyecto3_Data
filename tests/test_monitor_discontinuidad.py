"""Pruebas de funciones puras sin ejecutar la interfaz Streamlit."""
import ast
from pathlib import Path
import pandas as pd

RUTA = Path(__file__).resolve().parents[1] / 'pages' / '4_Monitor_Peten.py'


def funciones():
    arbol = ast.parse(RUTA.read_text(encoding='utf-8'))
    nombres = {'preparar_comparacion', 'variaciones_consecutivas'}
    nodos = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    espacio = {'pd': pd, 'datos_disponibles': lambda d, c: not d.empty and set(c).issubset(d.columns)}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), str(RUTA), 'exec'), espacio)
    return espacio


def muestra():
    return pd.DataFrame({
        'fecha': ['2025-12-01', '2026-03-01', '2026-04-01'],
        'indice_boletos_tikal': [100, 150, 165],
        'indice_pasajeros_aimm': [100, 120, 132],
        'indice_movilidad_poligono_aeropuerto': [100, 110, 121],
    })


def test_calendario_inserta_faltantes_sin_inventar_valores():
    d = funciones()['preparar_comparacion'](muestra())
    assert len(d) == 5
    assert d.loc[d.fecha.eq(pd.Timestamp('2026-01-01')), 'indice_boletos_tikal'].isna().all()
    assert d.loc[d.fecha.eq(pd.Timestamp('2026-02-01')), 'indice_boletos_tikal'].isna().all()


def test_marzo_no_compara_con_diciembre():
    d = funciones()['variaciones_consecutivas'](muestra())
    marzo = d[d.fecha.eq(pd.Timestamp('2026-03-01'))]
    assert marzo.variacion_pct.isna().all()


def test_abril_si_calcula_cambio_mensual():
    d = funciones()['variaciones_consecutivas'](muestra())
    abril = d[d.fecha.eq(pd.Timestamp('2026-04-01'))]
    assert len(abril) == 3
    assert all(abs(abril.variacion_pct - 10) < 1e-9)
