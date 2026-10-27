# Observatorio de Inteligencia Turística — Tikal y Flores, Petén

Proyecto académico de **Data Science** de la Universidad del Valle de Guatemala. El observatorio integra fuentes de movilidad, visitas a Tikal, actividad del Aeropuerto Internacional Mundo Maya (AIMM), hotelería y migración para apoyar el análisis del destino turístico de Tikal y Flores, Petén.

**Responsable:** Osman de León  
**Repositorio:** https://github.com/Emadlgg/proyecto3_Data.git  
**Estado:** prototipo funcional en Streamlit; procesamiento, indicadores y pronósticos implementados. Docker, revisión integral de interacciones y memoria técnica final pendientes.

> **Confidencialidad:** las bases institucionales se proporcionaron para uso académico. No publicar microdatos ni archivos originales en repositorios abiertos. Mantener el repositorio privado y compartir acceso únicamente con personas autorizadas por la cátedra. Verificar también los permisos antes de publicar archivos procesados o imágenes Docker.

## Objetivo

Construir un tablero interactivo para analizar la demanda turística, su comportamiento temporal, la oferta hotelera y las relaciones entre fuentes de información del destino. El tablero distingue datos observados de estimaciones y explica las limitaciones de cada fuente.

## Funcionalidades implementadas

La aplicación en **Python + Streamlit + Plotly** está organizada en cuatro módulos:

| Módulo | Contenido |
|---|---|
| **1. Demanda turística** | Visitantes por subdestino, estadía media ponderada, turistas y excursionistas, indicadores de composición. |
| **2. Temporalidad y predicciones** | Presencia diaria, patrones semanales, eventos, estimaciones de enero y febrero de 2026, métricas MAE y RMSE. |
| **3. Oferta hotelera** | Ocupación mensual, inventario de establecimientos, habitaciones y plazas cama, comparaciones en períodos coincidentes. |
| **4. Monitor especializado de Petén** | Comparación entre boletos de Tikal, pasajeros y operaciones del AIMM y movilidad por telefonía. |

Las páginas cuentan con filtros, gráficos interactivos y explicaciones. **La vinculación directa de al menos tres visualizaciones mediante selección en las propias gráficas aún requiere revisión funcional**; compartir filtros no equivale por sí solo a tener gráficas enlazadas.

## Estructura del repositorio

```text
proyecto3_Data/
├── app.py                       # Página principal de Streamlit
├── pages/
│   ├── 1_Demanda.py
│   ├── 2_Temporalidad.py
│   ├── 3_Hoteleria.py
│   └── 4_Monitor_Peten.py
├── src/
│   ├── __init__.py
│   ├── etl.py                    # Lectura y normalización de fuentes
│   ├── validaciones.py           # Auditoría de calidad y reporte JSON
│   ├── indicadores.py            # Cálculo de indicadores turísticos
│   ├── predicciones.py           # Estimaciones y evaluación retrospectiva
│   ├── visualizaciones.py        # Gráficas del módulo de demanda
│   └── visualizaciones_extra.py  # Funciones de otros módulos
├── notebooks/
│   ├── 01_exploracion.ipynb
│   ├── 02_limpieza_validacion.ipynb
│   ├── 03_indicadores.ipynb
│   └── 04_predicciones.ipynb
├── data/
│   ├── raw/                     # Fuentes originales (no publicar)
│   └── processed/
│       ├── indicadores/         # Indicadores derivados
│       └── predicciones/        # Estimaciones y métricas
├── tests/
│   ├── test_etl.py
│   ├── test_validaciones.py
│   ├── test_indicadores.py
│   ├── test_predicciones.py
│   ├── test_visualizaciones.py
│   └── test_modulos_234.py
├── docs/                        # Reportes y documentación
├── requirements.txt
├── .gitignore
└── README.md
```

La estructura muestra los archivos desarrollados hasta esta etapa. Los archivos locales de datos no necesariamente forman parte del repositorio remoto.

## Fuentes de datos

Se utilizan, según disponibilidad y permisos, los siguientes conjuntos de datos:

- **Movilidad por telefonía:** bases mensuales y diarias para Petén, con subdestinos como Isla de Flores, El Remate y el polígono del Aeropuerto Mundo Maya.
- **Visitantes de Tikal:** boletos de ingreso por mes y categoría.
- **AIMM:** pasajeros por flujo y tipo, así como operaciones aeronáuticas.
- **Hotelería:** ocupación mensual e inventarios de establecimientos, habitaciones y plazas cama.
- **Migración nacional:** `Base_Migracion_2009-2026jun.xlsx`, utilizada como referencia de estacionalidad.

Las encuestas de visitantes y residentes y la base complementaria podrán incorporarse en ampliaciones posteriores, previa validación de su alcance y uso autorizado.

### Reglas metodológicas importantes

- **No sumar subdestinos** de telefonía para obtener visitantes únicos de Petén: una misma persona puede aparecer en más de un polígono.
- **No sumar presencias diarias** para estimar visitantes únicos mensuales.
- Calcular la **estadía media ponderada** como días-persona / visitantes, únicamente para el segmento con pernocta (mayor a un día).
- Los meses sin cobertura telefónica **no son ceros**; las estimaciones deben identificarse como tales.
- **Boletos de Tikal, pasajeros del AIMM y telefonía** tienen universos y unidades diferentes; no deben sumarse ni equipararse directamente.
- Los inventarios hoteleros representan **cortes de capacidad**, no flujos acumulables. Los datos parciales de 2026 no deben anualizarse sin justificación.
- Los siete meses con cero registrados en la serie de Tikal requieren confirmación de su significado antes de interpretar sus causas.

## Instalación y ejecución local

Se recomienda **Python 3.12**. Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Colocar los archivos originales autorizados en `data/raw/` respetando los nombres y estructura esperados por `src/etl.py`. Ejecutar el procesamiento en este orden:

```powershell
python -m src.etl
python -m src.validaciones
python -m src.indicadores
python -m src.predicciones
```

Las salidas se generan en `data/processed/` y sus subcarpetas. El validador también genera `docs/reporte_validacion.json`. **No subir estas salidas al repositorio sin confirmar que su publicación esté autorizada.**

Iniciar el tablero:

```powershell
python -m streamlit run app.py
```

Abrir **http://localhost:8501** en el navegador.

Para trabajar con los notebooks, abrir `notebooks/` en VS Code o JupyterLab y seleccionar el intérprete del entorno `.venv`.

## Flujo reproducible

1. **Exploración:** `01_exploracion.ipynb` identifica fuentes, columnas, cobertura temporal y problemas iniciales.
2. **ETL:** `src/etl.py` transforma las fuentes sin sobrescribir los originales.
3. **Validación:** `src/validaciones.py` revisa archivos, rangos, claves y reglas de negocio; `02_limpieza_validacion.ipynb` documenta los hallazgos.
4. **Indicadores:** `src/indicadores.py` genera indicadores reutilizables; `03_indicadores.ipynb` presenta y examina resultados.
5. **Predicciones:** `src/predicciones.py` calcula estimaciones de enero-febrero de 2026 por subdestino y segmento, utilizando estacionalidad nacional y factores de reparto observados. `04_predicciones.ipynb` muestra metodología, resultados y validación retrospectiva.
6. **Visualización:** Streamlit consume los CSV procesados y permite explorar los resultados en cuatro módulos.

### Predicciones y limitaciones

Las predicciones de enero y febrero de 2026 se etiquetan como **estimaciones**, no como observaciones. La evaluación retrospectiva calcula **MAE y RMSE** en meses observados. Los resultados son exploratorios, dependen de los supuestos de estacionalidad y reparto, y **no representan un total único de visitantes de Petén**.

## Pruebas y estado de validación

Ejecutar:

```powershell
python -m pytest -v
```

**Última ejecución reportada (26 de octubre de 2026): 54 pruebas aprobadas en 1.27 s.** Cubren existencia y lectura de archivos, duplicados exactos, reglas de Tikal, ocupación, indicadores, predicciones y funciones de visualización. La aplicación también inició localmente en el puerto 8501.

Las pruebas automáticas no sustituyen la inspección visual de las cuatro páginas ni la revisión de todos los supuestos estadísticos. Durante la ejecución se observaron avisos de Streamlit por el uso de `use_container_width`; se recomienda sustituirlo por `width="stretch"` en los componentes correspondientes.

## Pendientes antes de la entrega final

- Verificar en el navegador los cuatro módulos, filtros y estados sin datos.
- Confirmar que **al menos tres visualizaciones estén vinculadas directamente** mediante interacciones.
- Revisar la precisión y limitaciones de los pronósticos y documentar hallazgos respaldados por evidencia.
- Resolver o documentar la interpretación de los meses con cero en Tikal.
- Preparar `Dockerfile` y `.dockerignore`, con una estrategia segura para proporcionar datos sin publicarlos en la imagen.
- Completar la memoria técnica y metodológica: arquitectura, catálogo de indicadores, fórmulas, fuentes, validación, limitaciones y recomendaciones para INGUAT.

## Tecnologías

Python, Pandas, NumPy, OpenPyXL, Streamlit, Plotly, Jupyter, scikit-learn / statsmodels (según análisis), Pytest. Docker está planificado para la fase de despliegue.

## Autoría y uso

Desarrollo académico individual: **Osman de León**. Universidad del Valle de Guatemala, 2026. Material de uso académico sujeto a las restricciones de confidencialidad establecidas por la cátedra y las instituciones proveedoras de datos.
