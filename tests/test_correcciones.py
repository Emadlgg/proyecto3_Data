"""Pruebas de las correcciones: selección única, huecos, tablas sin descarga y triangulación."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.ui.analitica import consumir_seleccion, completar_calendario
from src.triangulacion import (fuentes_mensuales, cobertura_fuentes, concordancia_pares,
                               indice_base_100, variacion_mensual_pct)
from src.visualizaciones_extra import ocupacion_y_afluencia

RAIZ = Path(__file__).resolve().parents[1]


# ---------- Bug de selección persistente (1_Demanda) ----------
def test_seleccion_nueva_se_aplica_una_sola_vez():
    estado = {}
    oct_ = pd.Timestamp('2025-10-01')
    assert consumir_seleccion(estado, 'k', oct_) == oct_
    assert consumir_seleccion(estado, 'k', oct_) is None  # mismo clic persistido en el rerun


def test_selector_lateral_no_se_revierte_por_seleccion_vieja():
    """Reproduce el bug: clic en octubre, luego la persona elige noviembre en la barra lateral."""
    estado, mes = {}, pd.Timestamp('2025-09-01')
    clic = pd.Timestamp('2025-10-01')
    nuevo = consumir_seleccion(estado, 'k', clic)          # rerun 1: clic en la barra
    if nuevo is not None and nuevo != mes:
        mes = nuevo
    assert mes == clic
    mes = pd.Timestamp('2025-11-01')                         # la persona cambia el selector
    nuevo = consumir_seleccion(estado, 'k', clic)          # rerun 2: la selección sigue guardada
    if nuevo is not None and nuevo != mes:
        mes = nuevo
    assert mes == pd.Timestamp('2025-11-01')                # no se revierte


def test_nuevo_clic_despues_de_otro_si_se_aplica_y_deseleccion_reinicia():
    estado = {}
    a, b = pd.Timestamp('2025-10-01'), pd.Timestamp('2025-12-01')
    consumir_seleccion(estado, 'k', a)
    assert consumir_seleccion(estado, 'k', b) == b
    assert consumir_seleccion(estado, 'k', None) is None    # deselección
    assert consumir_seleccion(estado, 'k', b) == b          # volver a elegir el mismo mes funciona


# ---------- Huecos: la ausencia no es cero ni se interpola ----------
def test_completar_calendario_mensual_deja_nan_en_huecos():
    d = pd.DataFrame({'fecha': pd.to_datetime(['2025-12-01', '2026-03-01']), 'v': [10.0, 20.0]})
    out = completar_calendario(d)
    assert out.fecha.dt.strftime('%Y-%m').tolist() == ['2025-12', '2026-01', '2026-02', '2026-03']
    assert out.v.isna().tolist() == [False, True, True, False]   # ni ceros ni interpolación


def test_completar_calendario_diario():
    d = pd.DataFrame({'fecha': pd.to_datetime(['2026-01-01', '2026-01-04']), 'v': [1.0, 4.0]})
    out = completar_calendario(d, freq='D')
    assert len(out) == 4 and out.v.isna().sum() == 2


def test_completar_calendario_por_grupo_sin_extrapolar():
    d = pd.DataFrame({'fecha': pd.to_datetime(['2025-01-01', '2025-03-01', '2025-02-01']),
                      'g': ['A', 'A', 'B'], 'v': [1.0, 3.0, 9.0]})
    out = completar_calendario(d, grupos=['g'])
    a = out[out.g.eq('A')]
    assert len(a) == 3 and a.v.isna().sum() == 1
    b = out[out.g.eq('B')]
    assert len(b) == 1 and b.fecha.iloc[0] == pd.Timestamp('2025-02-01')  # B no se extiende a otros meses
    assert list(out.columns) == ['fecha', 'g', 'v']


def test_completar_calendario_rechaza_duplicados_y_acepta_vacio():
    d = pd.DataFrame({'fecha': pd.to_datetime(['2025-01-01'] * 2), 'v': [1, 2]})
    with pytest.raises(ValueError):
        completar_calendario(d)
    assert completar_calendario(pd.DataFrame()).empty


# ---------- Cruce ocupación–afluencia con telefonía ----------
def test_cruce_acepta_telefonia_y_mantiene_ventana():
    f = pd.to_datetime(['2025-08-01', '2025-09-01', '2025-12-01', '2026-01-01'])
    ocup = pd.DataFrame({'fecha': f, 'ocupacion_pct': [50, 60, 70, 80]})
    tel = pd.DataFrame({'fecha': f, 'visitantes': [1.0, 2.0, 3.0, 4.0]})
    out = ocupacion_y_afluencia(ocup, tel, columna='visitantes', nombre='afluencia')
    assert out.fecha.dt.month.tolist() == [9, 12] and out.afluencia.tolist() == [2.0, 3.0]
    out2 = ocupacion_y_afluencia(ocup, pd.DataFrame({'fecha': f, 'total': [1, 2, 3, 4]}))
    assert 'boletos_tikal' in out2.columns  # firma original intacta


# ---------- Triangulación ----------
def _fuentes():
    meses = pd.to_datetime(['2025-09-01', '2025-10-01', '2025-11-01', '2025-12-01', '2026-03-01'])
    tik = pd.DataFrame({'fecha': list(meses) + [pd.Timestamp('2026-01-01')],
                        'total': [100, 200, 300, 400, 250, 0]})  # el cero se trata como sin dato
    air = pd.DataFrame({'fecha': meses[:4].repeat(2), 'flujo': ['Entrada', 'Salida'] * 4,
                        'pasajeros': [10, 10, 20, 20, 30, 30, 40, 40]})
    mov = pd.DataFrame({'fecha': list(meses) * 2, 'subdestino': ['A'] * 5 + ['B'] * 5,
                        'visitantes': [1, 2, 3, 4, 5, 900, 900, 900, 900, 900]})
    return tik, air, mov


def test_fuentes_mensuales_no_suma_poligonos_ni_trata_cero_como_dato():
    tik, air, mov = _fuentes()
    w = fuentes_mensuales(tik, air, mov, 'A').set_index('fecha')
    assert w.loc['2025-10-01', 'telefonia'] == 2          # solo el polígono A
    assert w.loc['2025-10-01', 'pasajeros_aimm'] == 40    # entrada + salida del mes
    assert np.isnan(w.loc['2026-01-01', 'boletos_tikal'])  # cero de Tikal = sin dato
    assert np.isnan(w.loc['2026-02-01', 'telefonia'])       # mes calendario faltante queda vacío


def test_cobertura_y_concordancia_solo_meses_comunes():
    tik, air, mov = _fuentes()
    w = fuentes_mensuales(tik, air, mov, 'A')
    cob = cobertura_fuentes(w).set_index('fuente')
    assert cob.loc['Pasajeros AIMM', 'meses_con_dato'] == 4
    assert cob.loc['Telefonía (polígono)', 'meses_sin_dato_en_rango'] == 2  # ene y feb 2026
    pares = concordancia_pares(w).set_index('par')
    p = pares.loc['Boletos Tikal vs Telefonía (polígono)']
    assert p.meses_comunes == 5
    # variaciones comparables: solo entre meses adyacentes con dato (sep→oct, oct→nov, nov→dic)
    assert p.variaciones_comparables == 3 and p.misma_direccion_pct == 100.0
    assert pares.loc['Pasajeros AIMM vs Telefonía (polígono)', 'meses_comunes'] == 4


def test_correlacion_requiere_minimo_de_meses():
    tik, air, mov = _fuentes()
    w = fuentes_mensuales(tik, air, mov, 'A')
    assert concordancia_pares(w, minimo_meses=6).correlacion_niveles.isna().all()


def test_variacion_no_cruza_huecos():
    s = pd.Series([100.0, np.nan, 150.0, 300.0])
    v = variacion_mensual_pct(s)
    assert v.isna().tolist() == [True, True, True, False] and v.iloc[3] == 100.0


def test_indice_base_100_en_primer_mes_comun():
    tik, air, mov = _fuentes()
    w = fuentes_mensuales(tik, air, mov, 'A')
    idx, base = indice_base_100(w)
    assert base == pd.Timestamp('2025-09-01')
    fila = idx.set_index('fecha').loc['2025-12-01']
    assert fila.boletos_tikal == 400 and fila.telefonia == 400  # 4/1*100 y 400/100*100
    assert indice_base_100(w.assign(telefonia=np.nan)) == (None, None)


# ---------- Política: sin descargas masivas ----------
def test_ninguna_pagina_usa_st_dataframe_directo():
    for f in list((RAIZ / 'pages').glob('*.py')) + [RAIZ / 'app.py']:
        assert 'st.dataframe(' not in f.read_text(encoding='utf-8-sig'), f.name


def test_tabla_segura_limita_filas_y_estilos_ocultan_la_barra(monkeypatch):
    pytest.importorskip('streamlit')
    from src.ui import componentes, estilos
    visto = {}
    monkeypatch.setattr(componentes.st, 'dataframe', lambda df, **kw: visto.update(n=len(df), kw=kw))
    monkeypatch.setattr(componentes.st, 'caption', lambda *a, **k: visto.update(aviso=True))
    componentes.tabla_segura(pd.DataFrame({'x': range(500)}), max_filas=200)
    assert visto['n'] == 200 and visto['aviso'] and visto['kw']['hide_index'] is True
    html = []
    monkeypatch.setattr(estilos.st, 'markdown', lambda t, **k: html.append(t))
    estilos.aplicar_estilos()
    assert 'stElementToolbar' in html[0]
