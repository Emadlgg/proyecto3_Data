# Observatorio de Inteligencia Turística — Tikal y Flores, Petén

Proyecto del curso **CC3084 Data Science** · Universidad del Valle de Guatemala · Semestre II 2026.
Destino asignado: **Grupo 2 — Tikal y Flores (Petén)**. Reto analítico: **triangulación de tres fuentes independientes** (boletos de Tikal, operaciones y pasajeros del AIMM, y telefonía).

**Responsable:** Osman de León
**Repositorio:** https://github.com/Emadlgg/proyecto3_Data.git (privado)

> **Confidencialidad.** Las bases institucionales se entregaron solo para uso académico dentro del curso.
> No se redistribuyen, no se publican en repositorios abiertos y el tablero **no ofrece descargas de datos**.
> Este repositorio debe permanecer **privado**, con docentes y auxiliares como colaboradores.
> Los archivos originales y las salidas procesadas están excluidos por `.gitignore` y `.dockerignore`
> y **nunca se copian dentro de la imagen Docker**: se montan como volúmenes.

---

## Contenido

1. [Inicio rápido](#inicio-rápido)
2. [Qué incluye el tablero](#qué-incluye-el-tablero)
3. [Datos de entrada y cobertura](#datos-de-entrada-y-cobertura)
4. [Reglas metodológicas](#reglas-metodológicas)
5. [Estimación de enero–febrero 2026](#estimación-de-eneroferebrero-2026)
6. [Instalación y ejecución](#instalación-y-ejecución)
7. [Despliegue con Docker](#despliegue-con-docker)
8. [Pruebas](#pruebas)
9. [Estructura del repositorio](#estructura-del-repositorio)
10. [Stack tecnológico](#stack-tecnológico)
11. [Pipeline MLOps (opcional)](#pipeline-mlops-opcional)
12. [Estado y pendientes](#estado-y-pendientes)

---

## Inicio rápido

Requisitos: **Docker** con Docker Compose y los archivos originales proporcionados por la cátedra.

```bash
# 1. Colocar los 10 archivos originales en data/raw/ (ver lista en "Datos de entrada")

# 2. Generar los datos procesados (ETL + validación + indicadores + estimaciones)
docker compose --profile tools run --rm etl

# 3. Levantar el tablero
docker compose up --build dashboard
```

Abrir **http://localhost:8501**. Para detenerlo: `docker compose down`.

Si `data/processed/` ya existe, basta con el paso 3.

---

## Qué incluye el tablero

Aplicación **Streamlit + Plotly** con cuatro módulos obligatorios y una página complementaria.
En los módulos 1 a 4, una gráfica principal permite seleccionar puntos o barras y actualiza las demás vistas del mismo módulo (visualizaciones vinculadas).

| Módulo | Contenido |
|---|---|
| **Inicio** | Panorama de movilidad por polígono (Isla de Flores, El Remate, Aeropuerto Mundo Maya) y acceso a los módulos. |
| **1. Demanda** (`1_Demanda.py`) | KPIs (visitantes promedio por mes, días-persona, estadía media ponderada), segmentación turista/excursionista, comparación de polígonos y **Top 10 de mercados emisores** (extranjeros), con nacionales y extranjeros por separado. Selección de barra → actualiza composición y estadía del mes. |
| **2. Temporalidad** (`2_Temporalidad.py`) | Serie diaria con selector de eventos, **lift** de cada festividad frente a un día regular del mismo día de semana, patrón semanal y fin de semana vs. días hábiles, **estimación de ene–feb 2026** con validación (MAE, RMSE, MAPE) y estado de publicación MLOps. |
| **3. Hotelería** (`3_Hoteleria.py`) | Ocupación mensual 2023–2025, capacidad instalada anual 2022–2025 (establecimientos, habitaciones, plazas cama), **cruce ocupación–afluencia en la ventana sep–dic 2025** (boletos de Tikal o telefonía por polígono) y comparación territorial de polígonos sin sumarlos. |
| **4. Monitor de Petén** (`4_Monitor_Peten.py`) | Reto del destino: triangulación de Tikal, AIMM y telefonía con índices base 100, variaciones mensuales entre meses consecutivos, **cobertura y concordancia entre fuentes** (correlación y coincidencia de dirección en meses comunes), boletos de Tikal y AIMM (pasajeros y operaciones en gráficas separadas). |
| **5. Perfil del visitante** (`5_Perfil_Visitante.py`) | Encuesta de visitantes 2025 en porcentajes muestrales, sin expansión poblacional. |

### Paleta de color

Documentada en [`docs/paleta_color.md`](docs/paleta_color.md) y definida en `src/ui/paleta.py`.
Principio central: **lo observado es azul sólido y lo estimado es terracota punteado y etiquetado «Estimación»**; ese color no se usa para nada más.

---

## Datos de entrada y cobertura

Los originales se colocan en `data/raw/` (solo lectura; el código nunca los modifica):

| Archivo | Uso |
|---|---|
| `BD_moviidad_mensual.xlsx` | Telefonía mensual por polígono y segmento; mercados emisores |
| `BD_moviidad_diario.xlsx` | Presencia diaria por polígono y tipo de día |
| `Visitantes_Tikal_2017-2026.xlsx` | Boletos de ingreso a Tikal |
| `AIMM_Consolidado_2022-2025.xlsx`, `AIMM_Aerolineas_2023-2026.xlsx` | Pasajeros del aeropuerto |
| `AIMM_Operaciones_Aeronauticas_2022-2026.xlsx` | Operaciones aéreas (no son personas) |
| `indice_ocupacion_mensual_2023_2025_1.csv` | Ocupación hotelera departamental |
| `oferta_hotelera_2022_2026.csv` | Inventario de establecimientos, habitaciones y plazas cama |
| `Base_Migracion_2009-2026jun.xlsx` | Migración nacional: perfil estacional y referencia de la estimación |
| `Encuesta_visitante_Peten_2025.xlsx` | Perfil y satisfacción (módulo 5) |

Cobertura temporal tras el procesamiento:

| Fuente | Cobertura | Observación |
|---|---|---|
| Telefonía mensual | sep 2025 – ago 2026 | **Sin cobertura en ene–feb 2026** |
| Telefonía diaria | abr 2025 – sep 2026 | Con huecos (p. ej. abr–ago 2025 y ene–feb 2026) |
| Boletos de Tikal | ene 2017 – ago 2026 | Siete meses con total cero: abr–sep 2020 (cierre del parque por COVID-19) y ene 2017 (inicio de serie, sin registro). Se tratan como «sin dato»; feb 2017 es registro parcial |
| AIMM | ene 2022 – abr 2026 | |
| Ocupación hotelera | ene 2023 – dic 2025 | Serie continua |
| Inventario hotelero | 2022 – 2025 (corte al 4.º trimestre) + 2026 (1.º trimestre parcial) | 2026 no se compara con años completos |

---

## Reglas metodológicas

Las seis reglas de la guía del proyecto están aplicadas y cubiertas por pruebas automáticas:

1. **Ausencia de dato no es cero.** Los meses sin cobertura se muestran como hueco («Sin dato»); las líneas se cortan en lugar de unir puntos vecinos (`completar_calendario`).
2. **No se promedia la permanencia promedio.** La estadía media es `suma de días-persona / suma de visitantes`, solo sobre el segmento «mayor a 1 día».
3. **No se suma la base diaria para obtener el mes.** La serie diaria solo se resume con medias y comparaciones.
4. **No se suman subdestinos.** Cada polígono se interpreta por separado: un visitante puede aparecer en más de uno.
5. **No se mezclan aeronaves con personas.** Operaciones y pasajeros van en gráficas independientes.
6. **No se extrapolan encuestas.** Se reportan como porcentajes de la muestra, recalculando la base válida en cada agregación.

Reglas adicionales: boletos de Tikal, pasajeros del AIMM y telefonía son universos distintos (solo se comparan variaciones relativas); los inventarios hoteleros son cortes de capacidad, no flujos; y los datos de 2026 no se anualizan.

---

## Estimación de enero–febrero 2026

La telefonía no tiene cobertura en esos dos meses, pero sí antes (sep–dic 2025) y después (mar–ago 2026).

- **Método principal.** `visitantes(t) = factor_reparto(t) × migración_nacional(t)`. El factor de reparto (visitantes del polígono ÷ migración nacional, de `Base_Migracion`) se interpola entre dic 2025 y mar 2026.
- **Alternativa con perfil estacional.** Usa el perfil estacional de migración en lugar de la migración observada. Se conserva en el tablero como línea tenue. Sobrestimó la migración nacional de ene–feb 2026 en 39 % y 46 %, y por eso no es el método principal.
- **Validación.** Se ocultan dos meses consecutivos con vecinos observados en ambos lados, se reconstruyen y se miden MAE, RMSE y MAPE. La muestra es pequeña (2 ventanas × 6 grupos × 2 meses), así que los resultados son indicativos.
- **Resultado de la corrida del 11-nov-2026.** El método principal obtuvo MAPE 6.4 %; la interpolación lineal de referencia, que no usa migración, 6.0 %. El tablero lo muestra en una nota de transparencia. Detalle en `data/processed/predicciones/backtest_imputacion_resumen.csv`.
- **Etiquetado.** Toda cifra estimada se rotula **«Estimación»** y usa el color terracota, separado de lo observado.

---

## Instalación y ejecución

Se recomienda **Python 3.12**.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
```

Con los originales en `data/raw/`, ejecutar el procesamiento **en este orden**:

```bash
python -m src.etl                 # lectura y normalización de las fuentes
python -m src.validaciones        # auditoría de calidad → docs/reporte_validacion.json
python -m src.indicadores         # indicadores reutilizables
python -m src.mercados_emisores   # Top de nacionalidades por polígono
python -m src.predicciones        # método base y perfil estacional nacional
python -m src.imputacion          # estimación ene–feb 2026 + backtest
python -m src.encuestas           # perfil y satisfacción (muestral)
```

Iniciar el tablero:

```bash
python -m streamlit run app.py
```

Abrir **http://localhost:8501**. Los notebooks de `notebooks/` documentan cada etapa (exploración, limpieza, indicadores, predicciones, encuestas y diagnóstico de modelos); se abren con JupyterLab o VS Code usando el entorno `.venv`.

---

## Despliegue con Docker

La solución está contenerizada. La imagen contiene solo el código; **los datos se montan como volúmenes**.

| Servicio | Perfil | Función |
|---|---|---|
| `dashboard` | (por defecto) | Tablero en `http://localhost:8501`, con `data/processed` y `artifacts` montados **solo lectura** |
| `etl` | `tools` | Ejecuta todo el procesamiento; `data/raw` se monta **solo lectura** |
| `mlflow` | `tools` | Servidor de seguimiento de experimentos (puerto 5000) |
| `pipeline` | `tools` | Pipeline MLOps con evaluación y publicación controlada |

Comandos habituales:

```bash
docker compose --profile tools run --rm etl      # genera data/processed
docker compose up --build dashboard              # inicia el tablero
docker compose down                              # detiene los servicios
```

**Dos imágenes.** Por defecto se instalan solo las dependencias del tablero y del ETL (`requirements-app.txt`, imagen ligera). Los servicios `mlflow` y `pipeline` se construyen con `requirements.txt` completo.

**Instalación en un servidor.**

1. Instalar Docker y Docker Compose.
2. Clonar el repositorio privado y copiar los originales a `data/raw/` por un canal autorizado.
3. Ejecutar el ETL y levantar el tablero con los dos comandos anteriores. El contenedor tiene `HEALTHCHECK` y `restart: unless-stopped`.
4. Por seguridad, los puertos están publicados únicamente en `127.0.0.1`. Para acceso externo, colocar un proxy inverso (por ejemplo Nginx o Caddy) con HTTPS y autenticación, en lugar de abrir el puerto directamente.

---

## Pruebas

```bash
python -m pytest -v
```

Cubren lectura y calidad de las fuentes, reglas de negocio (estadía ponderada, subdestinos, huecos, cortes de inventario, ventana sep–dic 2025), indicadores, estimación y backtest, triangulación y la política de no descarga de datos. Las funciones puras se prueban sin ejecutar Streamlit.

---

## Estructura del repositorio

```text
proyecto3_Data/
├── app.py                       # Inicio del tablero
├── pages/                       # Módulos 1–4 y perfil del visitante
├── src/
│   ├── etl.py                   # Lectura y normalización de las fuentes
│   ├── validaciones.py          # Auditoría de calidad
│   ├── indicadores.py           # Indicadores turísticos
│   ├── mercados_emisores.py     # Top de nacionalidades por polígono
│   ├── predicciones.py          # Método base y perfil estacional
│   ├── imputacion.py            # Estimación ene–feb 2026 y backtest
│   ├── triangulacion.py         # Cobertura y concordancia entre fuentes
│   ├── encuestas.py             # Perfil y satisfacción muestral
│   ├── visualizaciones*.py      # Gráficas y funciones de los módulos
│   ├── ui/                      # Paleta, estilos, componentes y utilidades del tablero
│   └── pipeline.py, evaluacion*.py, optimizacion*.py, publicacion.py,
│       monitoreo.py, mlflow_tracking.py   # MLOps y diagnóstico de modelos
├── config/mlops.json            # Parámetros y umbrales del pipeline
├── notebooks/                   # 01 exploración … 06 diagnóstico de modelos
├── tests/                       # Pruebas automáticas
├── data/
│   ├── raw/                     # Originales (no se versionan)
│   └── processed/               # Salidas del ETL (no se versionan)
├── artifacts/                   # Corridas y evidencia del pipeline (no se versiona)
├── docs/                        # Paleta de color y reporte de validación
├── labs/                        # Entregas de laboratorios 10, 11 y 12
├── scripts/organizar_proyecto.py
├── Dockerfile · compose.yaml · .dockerignore
├── requirements.txt             # Desarrollo completo
├── requirements-app.txt         # Solo tablero y ETL (imagen Docker)
└── .streamlit/config.toml       # Tema visual
```

`labs/` contiene informes y material de laboratorios anteriores y **no forma parte del tablero**. Si se conserva en el repositorio, verificar que `labs/lab12_powerbi/powerbi/*.pbix` no incluya datos institucionales importados.

---

## Stack tecnológico

Todo el proyecto usa herramientas **de código abierto y gratuitas**, sin herramientas comerciales propietarias.

| Componente | Herramienta | Motivo |
|---|---|---|
| Procesamiento y estimación | Python 3.12, pandas, NumPy, OpenPyXL | Lectura de Excel/CSV, transformaciones reproducibles y estimación con métodos propios (interpolación del factor de reparto) |
| Tablero | Streamlit | Interacción por selección de puntos con poco código; una sola base Python para ETL y visualización |
| Gráficas | Plotly | Gráficas interactivas y responsivas |
| Despliegue | Docker y Docker Compose | Entorno reproducible para calificar y desplegar |
| Seguimiento | MLflow | Trazabilidad de corridas de evaluación |
| Calidad | pytest | Pruebas de reglas metodológicas |
| Notebooks | Jupyter | Documentación de cada etapa del análisis |

La justificación ampliada del stack está en la Memoria Técnica.

---

## Pipeline MLOps (opcional)

Parte del laboratorio 11. Evalúa un candidato de estimación con *rolling origin* (oct–dic 2025, sin información futura), lo compara con una referencia y **publica solo si cumple umbrales fijados de antemano**: razón de MAE ≤ 1.0 respecto a la referencia y nMAE ≤ 0.35 (`config/mlops.json`).

```bash
docker compose --profile tools up -d mlflow       # http://localhost:5000
docker compose --profile tools run --rm pipeline
python -m src.monitoreo --data data/processed --config config/mlops.json
```

**Estado actual.** La última ejecución rechazó al candidato (razón de MAE 1.86 > 1.0), por lo que **no hay versión oficial publicada**. El pipeline evalúa el método anterior (factor mediano × perfil estacional). Las estimaciones que muestra el módulo 2 provienen de `src.imputacion`, validada con su propio backtest, y se presentan siempre como exploratorias.

---

## Limitaciones conocidas

- Telefonía sin cobertura en ene–feb 2026; no hay comparación interanual directa entre 2025 y 2026.
- Las estimaciones tienen validación sobre pocas observaciones y no representan un total único de visitantes de Petén.
- Los datos hoteleros de 2026 son parciales (primer trimestre) y repiten valores de 2025 en parte de las combinaciones.
- El AIMM llega hasta abril de 2026; por eso la triangulación de tres fuentes cubre solo seis meses comunes.
- Las encuestas no tienen factor de expansión: sus porcentajes no se extrapolan a totales.

## Autoría y uso

Desarrollo académico: **Osman de León**. Universidad del Valle de Guatemala, 2026.
Material de uso académico, sujeto a las restricciones de confidencialidad de la cátedra y de las instituciones proveedoras de datos.