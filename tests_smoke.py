from pathlib import Path
import pandas as pd
root=Path(__file__).parent/'data'
t=pd.read_csv(root/'serie_mensual_total.csv',parse_dates=['fecha'])
v=pd.read_csv(root/'serie_mensual_por_via.csv',parse_dates=['fecha'])
m=pd.read_csv(root/'final_metricas_modelos.csv')
p=pd.read_csv(root/'final_pronostico_prueba_intervalo80.csv')
assert len(t)==len(v)==210
assert len(m)>=3
assert {'MAE','RMSE'}.issubset(m.columns)
assert {'observado','estimacion','limite_inferior_80','limite_superior_80'}.issubset(p.columns)
assert (t.viajeros-v[['Aérea','Marítima','Terrestre']].sum(axis=1)).abs().max()<0.01
print('OK: archivos y consistencia de series verificadas')
