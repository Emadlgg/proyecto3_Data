# Laboratorio 10 — Visualización interactiva

**Autor:** Osman de León  
**Repositorio:** https://github.com/Emadlgg/proyecto3_Data.git

## Ejecutar

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Requiere Streamlit con soporte de `on_select` en `st.plotly_chart` (versiones recientes).

## Contenido

- 8 visualizaciones interactivas repartidas entre las páginas **Exploración** (1–6) y **Predicciones y modelos** (7–8).
- 3 visualizaciones enlazadas: selección de año (gráfica 1) modifica la gráfica 2 y la 3; selección de mes (gráfica 2) modifica la gráfica 3.
- Comparación de 4 modelos reutilizados; MAE y RMSE, más pronóstico observado/estimado e intervalo del 80 %.
- Selector de año, mes, vía, sección y métrica.

**Alcance:** datos nacionales de migración; no representan la demanda específica de Tikal y Flores. El proyecto turístico de Petén exige otras fuentes que no están disponibles aquí.

**Confidencialidad:** los CSV incluidos son salidas procesadas del trabajo previo. Antes de publicarlos, confirmar con la cátedra si pueden distribuirse. Si no, eliminarlos del repositorio y proveerlos por una vía privada autorizada.

## Verificación

El script `tests_smoke.py` verifica estructura, fuentes y consistencia numérica. También se debe comprobar manualmente la interacción en el navegador.
