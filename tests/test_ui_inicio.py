import pandas as pd
import plotly.graph_objects as go
from src.ui.datos import panorama
from src.ui.graficas import aplicar_tema


def test_panorama_sin_archivos(tmp_path):
    p = panorama(tmp_path)
    assert p['subdestinos'] is None
    assert p['meses_movilidad'] is None
    assert p['movilidad'].empty


def test_panorama_no_suma_subdestinos(tmp_path):
    pd.DataFrame([
        {'fecha': '2025-09-01', 'subdestino': 'Flores', 'segmento': 'mayor a 1 dia', 'visitantes': 12},
        {'fecha': '2025-09-01', 'subdestino': 'Remate', 'segmento': 'mayor a 1 dia', 'visitantes': 9},
    ]).to_csv(tmp_path / 'movilidad_mensual_peten.csv', index=False)
    p = panorama(tmp_path)
    assert p['subdestinos'] == 2
    assert p['meses_movilidad'] == 1
    assert 'visitantes_total_peten' not in p


def test_grafica_conserva_trazas():
    fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
    assert len(aplicar_tema(fig).data) == 1
