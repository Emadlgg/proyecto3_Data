
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"

ARCHIVOS = [
    "movilidad_mensual_peten.csv",
    "movilidad_diaria_peten.csv",
    "tikal_mensual.csv",
    "aimm_pasajeros_mensual.csv",
    "aimm_operaciones_mensual.csv",
    "ocupacion_peten.csv",
    "oferta_hotelera_peten.csv",
    "migracion_nacional_mensual.csv",
    "comparacion_fuentes_peten.csv",
]


@pytest.mark.parametrize("archivo", ARCHIVOS)
def test_archivo_existe(archivo):
    assert (DATA / archivo).is_file()


@pytest.mark.parametrize("archivo", ARCHIVOS)
def test_archivo_no_vacio(archivo):
    df = pd.read_csv(DATA / archivo)
    assert not df.empty


@pytest.mark.parametrize("archivo", ARCHIVOS)
def test_sin_duplicados_exactos(archivo):
    df = pd.read_csv(DATA / archivo)
    assert not df.duplicated().any()


def test_tikal_totales():
    df = pd.read_csv(DATA / "tikal_mensual.csv")

    calculado = (
        df["nacionales"]
        + df["extranjeros"]
        + df["otros"]
    )

    pd.testing.assert_series_equal(
        calculado,
        df["total"],
        check_names=False,
    )


def test_ocupacion_rango():
    df = pd.read_csv(DATA / "ocupacion_peten.csv")

    valores = pd.to_numeric(
        df["indice_ocupacion"],
        errors="coerce"
    )

    assert valores.notna().all()
    assert valores.ge(0).all()

    # Ajustar según la unidad documentada.
    if valores.max() <= 1:
        assert valores.le(1).all()
    else:
        assert valores.le(100).all()
