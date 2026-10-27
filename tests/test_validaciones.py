"""Pruebas de reglas y manejo de errores del auditor."""
import pandas as pd
from src.validaciones import evaluar, FILES


def test_reporta_archivos_faltantes(tmp_path):
    r = evaluar(tmp_path)
    assert len(r['errores']) == len(FILES)


def test_detecta_tikal_total_inconsistente(tmp_path):
    df = pd.DataFrame({'fecha':['2025-01-01'], 'nacionales':[3], 'extranjeros':[4], 'otros':[0], 'total':[99]})
    df.to_csv(tmp_path/'tikal_mensual.csv',index=False)
    r = evaluar(tmp_path)
    assert any('Tikal: total diferente' in e for e in r['errores'])


def test_no_modifica_archivos(tmp_path):
    p=tmp_path/'tikal_mensual.csv'
    p.write_text('fecha,nacionales,extranjeros,otros,total\n2025-01-01,1,2,0,3\n',encoding='utf-8')
    original=p.read_bytes()
    evaluar(tmp_path)
    assert p.read_bytes()==original
