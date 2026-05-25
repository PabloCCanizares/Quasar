# PreproLab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.

**Laboratorio dedicado al Tema 5 del temario — Preprocesamiento clásico con Spark.**

PreproLab implementa todas las técnicas del temario sobre un dataset sintético construido a propósito: una **flota de robots autónomos con mantenimiento predictivo**. El escenario incluye intencionadamente los 10 tipos de problemas que el alumno tiene que resolver: valores perdidos (MCAR/MAR/MNAR), outliers de tres tipos, class noise, duplicados, fechas en formatos múltiples, encoding roto, multivaluadas, redundancia entre atributos, etc.

## Estado actual: Fase 3 (bloque EDA operativo)

Dataset generado y primer bloque (EDA) completamente funcional con UI Plotly. Los bloques restantes se irán implementando en fases siguientes.

| Bloque | Técnicas planificadas | Estado |
|---|---|---|
| **Seed** | Generador de la flota de robots (4 tablas, 14 problemas inyectados) | **Fase 2 OK** |
| `eda` | Univariable, missing matrix, correlaciones — UI con Plotly | **Fase 3 OK** |
| `missing` | Diagnóstico MCAR/MAR/MNAR + Imputer (media/mediana), KNNI, KMI, MICE | Fase 4 |
| `outliers` | IQR, Z-score, boxplot + EF/CVCF/IPF noise filters | Fase 5 |
| `integration` | union, 4 tipos de joins, correlaciones para dedup | Fase 6 |
| `transform` | One-hot, ordinal, multi-flag, discretización (3 métodos), pivot/groupby | Fase 7 |
| `normalize` | Z-score, Min-Max, Robust, Decimal — comparados sobre mismo modelo | Fase 8 |
| `reduce_dim` | PCA, t-SNE, AutoEncoders + feature selection (filter/wrapper/embedded) | Fase 9 |
| `reduce_inst` | SRSWOR, estratificado, balanceado, K-Means compresión | Fase 10 |
| **Pipeline Studio** | UI para componer pipelines y comparar AUC/F1 sobre mismo modelo | Fase 11 |

### Bloque EDA (Fase 3) — detalle

Tres ejercicios scaffold/solución, todos sobre las 4 tablas del seed:

| Ejercicio | Endpoint | Qué calcula |
|---|---|---|
| EDA-1 | `GET /api/preprolab/eda/univariate/{tabla}/{columna}` | Media, mediana, std, min/max, Q1/Q3, histograma (numérica) o value_counts (categórica), + detección rápida IQR |
| EDA-2 | `GET /api/preprolab/eda/missing/{tabla}` | % null por columna + co-ocurrencia de nulls + interpretación heurística MCAR/MAR/MNAR |
| EDA-3 | `GET /api/preprolab/eda/correlations/{tabla}` | Matriz Pearson + pares más correlacionados + redundantes (|r| > 0.9) |

Endpoints no-gateados (siempre disponibles): `overview` y `schema/{tabla}`.

Frontend: tab EDA con selector de tabla, histogramas (Plotly bars), missing matrix visual, heatmap de correlaciones interactivo.

**Total previsto**: ~30 ejercicios con patrón scaffold/solución.

## Arranque rápido

```bash
# Desde la raíz del repo Quasar:
./lab.sh preprolab up        # Arranca app-preprolab + dependencias
./lab.sh preprolab status    # Estado actual
./lab.sh preprolab logs      # Logs del contenedor
./lab.sh preprolab down      # Para SOLO preprolab (mongo/neo4j siguen vivos)
```

Web: <http://localhost:8002>

## Modo laboratorio

Los bloques se desbloquean en runtime con flags `LAB_PREPROLAB` en `infra/compose/.env.docker`:

```bash
./lab.sh preprolab unlock eda          # Desbloquea EDA
./lab.sh preprolab unlock missing      # ...
./lab.sh preprolab solutions           # Desbloquea todos
./lab.sh preprolab exercises           # Bloquea todos (scaffold puro)
```

## Estructura del código

```text
apps/preprolab/
├── src/
│   ├── config/      # Configuración propia (importa de infra/shared/)
│   ├── web/         # FastAPI + SPA con Plotly.js
│   ├── seed/        # Generador del dataset sintético (Fase 2)
│   └── spark/       # Bloques de preprocesamiento (Fases 3-10)
├── main.py
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Dataset (Fase 2 — implementado)

4 tablas relacionadas con problemas inyectados intencionadamente. Para regenerar:

```bash
./lab.sh preprolab seed
```

Output (~17 MB total) en `infra/data/preprolab/raw/`, formato JSON Lines:

| Tabla | Registros aprox | Contenido |
|---|---|---|
| `robots.json` | ~2.060 | Catálogo de robots + variable objetivo (`failure_next_48h`). Incluye duplicados intencionados (~3%). |
| `sensors_readings.json` | ~98.000 | Telemetría temporal (60 días). Valores con MCAR y outliers de medición. |
| `events.json` | ~9.000 | Eventos etiquetados por operarios. Class noise (~5%) + PII plantada (~5%). |
| `maintenances.json` | ~3.000 | Historial de mantenimientos. Duraciones negativas como outliers fuera de rango. |

**Variable objetivo**: `robots.failure_next_48h` (1 si el robot falla en próximas 48h, 0 si no). ~24% positivos / ~76% negativos. Clasificación binaria recomendada con RandomForest o GBT.

**Problemas inyectados** (mapeados al Tema 5):

| # | Problema | Dónde aparece | Ratio |
|---|---|---|---|
| 1 | **MCAR** — valor null al azar | `sensors_readings.valor` | ~3% |
| 2 | **MAR** — depende de firmware viejo | `robots.battery_health_v2` | ~30% de robots |
| 3 | **MNAR** — depende del valor oculto | `robots.consumo_kw` (Manufactura Centauri) | ~25% de robots |
| 4 | Outliers de medición | `sensors_readings.temperatura = 1000` | ~0.5% |
| 5 | Outliers extremos válidos | bateria_pct=100, voltaje=60, temp=85 | ~0.2% |
| 6 | Outliers fuera de rango | fechas futuras, duraciones negativas | ~0.2% |
| 7 | **Class noise** | `events.tipo` + `events.severidad` | ~5% |
| 8 | **Duplicados** | robots clonados con encoding alterado | ~3% |
| 9 | **Fechas en 5 formatos** | todas las fechas (epoch / ISO / US / EU / relativo) | ~20% cada uno |
| 10 | **Encoding roto** | nombres de técnicos y almacenes con mojibake | ~5% |
| 11 | **Multivaluadas** | `robots.sensores_activos` como CSV | 100% |
| 12 | **Redundancia** | `bateria_pct`, `voltaje_v`, `consumo_total_kwh` correlacionados | 100% |
| 13 | PII plantada | emails y teléfonos en `events.descripcion` | ~5% |
| 14 | Descripciones extremas | vacías o de 5000 caracteres | ~3% |

Todos los ratios verificables en la salida del comando seed.

## API expuesta

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | `{"status": "ok", "app": "preprolab"}` |
| `GET /api/preprolab/lab/status` | Bloques desbloqueados según `LAB_PREPROLAB` |

Endpoints de cada bloque se añadirán según avancen las fases.
