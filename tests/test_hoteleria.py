"""Pruebas de las reglas hoteleras sin ejecutar la interfaz Streamlit."""
import ast
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pages" / "3_Hoteleria.py"


def funciones():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    names = {"inventario_anual", "comparacion_poligonos"}
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = {"pd": pd}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


def test_inventario_elige_ultimo_corte_sin_sumar():
    f = funciones()["inventario_anual"]
    d = pd.DataFrame({"anio": [2025, 2025], "trimestre": [1, 4],
                      "tipo_alojamiento": ["Hotel", "Hotel"],
                      "establecimientos": [10, 12], "habitaciones": [100, 120], "plazas_cama": [200, 240]})
    r = f(d)
    assert len(r) == 1
    assert r.iloc[0].habitaciones == 120


def test_excluye_2026_parcial():
    f = funciones()["inventario_anual"]
    d = pd.DataFrame({"anio": [2025, 2026], "tipo_alojamiento": ["Hotel", "Hotel"],
                      "establecimientos": [10, 20], "habitaciones": [100, 200], "plazas_cama": [200, 400]})
    assert f(d).anio.tolist() == [2025]


def test_rechaza_cortes_duplicados_sin_trimestre():
    f = funciones()["inventario_anual"]
    d = pd.DataFrame({"anio": [2025, 2025], "tipo_alojamiento": ["Hotel", "Hotel"],
                      "establecimientos": [10, 20], "habitaciones": [100, 200], "plazas_cama": [200, 400]})
    with pytest.raises(ValueError):
        f(d)


def test_comparacion_no_suma_poligonos():
    f = funciones()["comparacion_poligonos"]
    d = pd.DataFrame({"fecha": ["2025-09-01", "2025-09-01"],
                      "subdestino": ["Flores", "Remate"], "visitantes": [10, 20]})
    r = f(d, "2025-09-01")
    assert len(r) == 2
    assert set(r.subdestino) == {"Flores", "Remate"}


def test_cruce_estricto_en_funcion_existente():
    from src.visualizaciones_extra import ocupacion_y_afluencia
    fechas = pd.to_datetime(["2025-08-01", "2025-09-01", "2025-12-01", "2026-01-01"])
    o = pd.DataFrame({"fecha": fechas, "ocupacion_pct": [20, 30, 40, 50]})
    t = pd.DataFrame({"fecha": fechas, "total": [100, 200, 300, 400]})
    r = ocupacion_y_afluencia(o, t)
    assert r.fecha.dt.strftime("%Y-%m").tolist() == ["2025-09", "2025-12"]
