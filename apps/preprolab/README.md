# PreproLab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.

**Laboratorio dedicado al Tema 5 del temario — Preprocesamiento clásico con Spark.**

PreproLab implementa todas las técnicas del temario sobre un dataset sintético construido a propósito: una **flota de robots autónomos con mantenimiento predictivo**. El escenario incluye intencionadamente los 10 tipos de problemas que el alumno tiene que resolver: valores perdidos (MCAR/MAR/MNAR), outliers de tres tipos, class noise, duplicados, fechas en formatos múltiples, encoding roto, multivaluadas, redundancia entre atributos, etc.

## Estado actual: Fase 7 (bloque transform operativo)

Dataset generado, EDA + missing + outliers + integration + transform funcionales. Los bloques restantes se irán implementando en fases siguientes.

| Bloque | Técnicas planificadas | Estado |
|---|---|---|
| **Seed** | Generador de la flota de robots (4 tablas, 14 problemas inyectados) | **Fase 2 OK** |
| `eda` | Univariable, missing matrix, correlaciones — UI con Plotly | **Fase 3 OK** |
| `missing` | Drop + simple (mean/median/mode) + KNN + KMeans + comparativa antes/después | **Fase 4 OK** |
| `outliers` | IQR + Z-score + gestión (remove/cap/log) + noise filters EF/CVCF/IPF | **Fase 5 OK** |
| `integration` | union + 4 joins + Pearson + Cramér's V + dedup por correlación | **Fase 6 OK** |
| `transform` | One-hot + ordinal + multi-flag CSV + discretización (eq-width/eq-freq/MDLP) + groupby | **Fase 7 OK** |
| `normalize` | Z-score + Min-Max + Robust + Decimal Scaling + comparativa con detección de outliers | **Fase 8 OK** |
| `reduce_dim` | PCA + t-SNE + feature selection Filter / Wrapper / Embedded + comparador de las 3 familias | **Fase 9 OK** |
| `reduce_inst` | SRSWOR + estratificado + balanceado + por clusters + K-Means compresión | **Fase 10 OK** |
| **★ Pipeline Studio** | Compose pipelines + RF training + comparativa AUC/F1/ROC entre N configuraciones | **Fase 11 OK** |
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

### Bloque MISSING (Fase 4) — detalle

Cinco ejercicios sobre las 4 estrategias del Tema 5 + comparativa final:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| MISSING-1 | `GET /api/preprolab/missing/dropna/{tabla}?mode=any\|all\|thresh` | `.dropna()` con varias estrategias |
| MISSING-2 | `GET /api/preprolab/missing/impute_simple/{tabla}/{columna}?strategy=mean\|median\|mode` | Imputer pyspark-style (constante por columna) |
| MISSING-3 | `GET /api/preprolab/missing/impute_knn/{tabla}/{columna}?k=N` | KNN Imputation (sklearn KNNImputer + StandardScaler) |
| MISSING-4 | `GET /api/preprolab/missing/impute_kmeans/{tabla}/{columna}?k=N` | K-Means Imputation: imputación temporal con mediana → KMeans → reemplazar nulls con centroide |
| MISSING-5 | `GET /api/preprolab/missing/compare/{tabla}/{columna}` | Aplica los 5 métodos a una columna y compara distribuciones + variance loss |

Endpoint no-gateado (siempre disponible): `columns_with_nulls/{tabla}`.

Frontend: tab "Valores perdidos" con 5 secciones colapsables, una por técnica. Cada sección tiene controles propios (modo dropna, estrategia simple, k para KNN/KMeans) y muestra:
- Estadísticas antes/después de la imputación (mean, median, std, min/max, % null).
- Histogramas superpuestos (gris = antes, azul = después).
- Para KMeans: distribución por cluster con tamaño + imputados + valor del centroide.
- Para compare: 5 histogramas superpuestos + tabla de variance loss por método.

Validación verificada sobre `robots.battery_health_v2` (27.91% null por MAR del firmware viejo):

| Método | std resultante | variance loss vs drop |
|---|---|---|
| drop (referencia) | 0.1702 | 0 (ref) |
| mean | 0.1445 | -15.1% |
| median | 0.1445 | -15.1% |
| **KNN k=5** | **0.1509** | **-11.3%** (mejor) |
| KMeans k=5 | 0.1448 | -14.9% |

El alumno ve numérica y visualmente por qué KNN/KMeans son mejores que mean/median: capturan correlaciones con otras features (especialmente firmware_version, que es la causa real del MAR).

### Bloque OUTLIERS (Fase 5) — detalle

Cuatro ejercicios sobre detección/gestión de outliers numéricos + class noise filters:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| OUTLIERS-1 | `GET /api/preprolab/outliers/detect_iqr/{tabla}/{columna}?multiplier=N` | IQR: Q1 - N·IQR / Q3 + N·IQR (N=1.5 clásico) + boxplot data |
| OUTLIERS-2 | `GET /api/preprolab/outliers/detect_zscore/{tabla}/{columna}?threshold=T` | Z-score: outlier si |z| > T (T=3.0 default) |
| OUTLIERS-3 | `GET /api/preprolab/outliers/handle/{tabla}/{columna}?strategy=remove\|cap\|log` | Gestión: eliminar filas, winsorize, log-transform |
| OUTLIERS-4 | `GET /api/preprolab/outliers/noise_filter/{tabla}?method=ef\|cvcf\|ipf&inject_noise_pct=X` | Noise Filters del Tema 5 con validación opcional con ground truth |

Validación verificada sobre `sensors_readings.temperatura` (491 valores =1000°C inyectados como outliers de medición, 0.5%):

- **IQR mult=1.5**: bounds [-0.3, 80.5], detecta 673 outliers (0.68% — incluye los 1000°C y algunos extremos válidos a 85°C).
- **Z-score th=3.0**: detecta 491 (los 1000°C puros, con z=13.92).
- **cap (winsorize) tras IQR**: std baja de 68.63 → 12.00, max de 1000 → 80.5. Dataset completo preservado.

Y para `robots.failure_next_48h` con 10% ruido inyectado a propósito (ground truth conocido):

| Filter | Detectados | Recall | Precision | F1 | Iteraciones |
|---|---|---|---|---|---|
| **EF** (conservador, 3 clasificadores) | 16.75% | 0.558 | 0.332 | 0.416 | 1 |
| **CVCF** (moderado, k DecisionTree por mayoría) | 17.46% | 0.575 | 0.328 | 0.418 | 1 |
| **IPF** (agresivo, iterativo hasta convergencia) | 19.58% | 0.593 | 0.302 | 0.400 | 5 |

Coherente con el PDF: recall sube monotónicamente al pasar de conservador → moderado → agresivo, y precision baja por más falsos positivos. El parámetro `inject_noise_pct` permite al alumno validar la calidad del detector con ground truth, no solo creérsela.

### Bloque INTEGRATION (Fase 6) — detalle

Cuatro ejercicios sobre integración de datos y detección de redundancia:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| INTEG-1 | `GET /api/preprolab/integration/union/{a}/{b}?same_schema_only=true\|false` | `pd.concat` con detección de incompatibilidades + modo permisivo |
| INTEG-2 | `GET /api/preprolab/integration/join/{a}/{b}?on=col&how=inner\|left\|right\|outer` | Los 4 tipos de unión SQL + cardinalidad de keys |
| INTEG-3 | `GET /api/preprolab/integration/find_redundancy/{tabla}?threshold=T` | Pearson para numéricas + Cramér's V para categóricas |
| INTEG-4 | `GET /api/preprolab/integration/dedup_by_correlation/{tabla}?threshold=T` | Aplica el drop sugerido por INTEG-3 |

Validación end-to-end:

- **union robots ⊔ events**: schemas incompatibles, `mode=blocked`. Coherente: estas tablas no pueden unirse verticalmente (cero columnas comunes).
- **join events ⋈ maintenances on robot_id (inner)**: 9.088 ⋈ 3.012 = 13.977 filas. Keys: 1.819 robots en events, 1.679 en maint, 1.527 comunes.
- **find_redundancy(robots, 0.9)** detecta los 3 pares que el seed inyectó deliberadamente:
  - voltaje_v ↔ consumo_total_kwh: r = 0.9939
  - bateria_pct ↔ voltaje_v: r = 0.9925
  - bateria_pct ↔ consumo_total_kwh: r = 0.9901
  Y sugiere eliminar `consumo_total_kwh` y `voltaje_v`, conservando `bateria_pct` (la de mayor varianza).
- **dedup_by_correlation(robots, 0.9)**: 14 → 12 columnas (-14.29%).

Cramér's V se implementa manualmente (sin scipy) calculando el chi² de la tabla de contingencia y normalizando por `sqrt(n · min(c-1, r-1))`. Es la generalización natural de Phi para categóricas r×c.

### Bloque TRANSFORM (Fase 7) — detalle

Cinco ejercicios sobre conversiones y discretización del Tema 5:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| TRANS-1 | `GET /api/preprolab/transform/onehot/{tabla}/{columna}?max_categories=N` | One-hot con agrupación OTROS si hay >N valores |
| TRANS-2 | `GET /api/preprolab/transform/ordinal/{tabla}/{columna}?order=v1,v2,v3` | Ordinal con orden custom (ej. INFO,WARN,ERROR,CRITICAL) |
| TRANS-3 | `GET /api/preprolab/transform/multivalued/{tabla}/{columna}?separator=,` | CSV interno → flags binarios |
| TRANS-4 | `GET /api/preprolab/transform/discretize/{tabla}/{columna}?method=equal_width\|equal_freq\|mdlp&bins=N` | Equal-width, Equal-frequency o MDLP supervisado |
| TRANS-5 | `GET /api/preprolab/transform/groupby/{tabla}?by=col&agg_col=col&agg=mean\|sum\|...` | Agregación con groupby |

Validación end-to-end:

- **one-hot(robots.fabricante)** → 4 columnas binarias (Centauri/Orion/Sirius/Vega), distribución equilibrada.
- **ordinal(events.severidad, INFO<WARN<ERROR<CRITICAL)** → mapping 1→4, mean encoded = 2.51, mediana = 3 (events ligeramente sesgados a severidades altas).
- **multivalued(robots.sensores_activos)** → 9 flags binarios (battery, camera_depth, camera_rgb, encoder_wheel, imu, lidar_2d, lidar_3d, temp_cpu, temp_motor), cardinalidad media 4.94 sensores/robot (coincide con el seed `k=randint(3,7)`).
- **discretize equal_width(bateria_pct, 5)** → edges [20, 36, 52, 68, 84, 100], 5 grupos balanceados.
- **discretize MDLP(bateria_pct)** → edges [20.0, **28.1**, 29.8, 100.0]. El corte en 28.1 **detecta automáticamente el umbral `<30` que el seed inyecta** en la probabilidad de fallo, validando el algoritmo supervisado.
- **groupby(robots, by=fabricante, mean(bateria_pct))** → 4 fabricantes con batería media casi idéntica (59-62), coherente con el seed que distribuye uniforme.

MDLP (Fayyad-Irani) se implementa internamente: para cada segmento busca el corte que maximiza ganancia de información respecto al target, aplica criterio MDL para parar, y recursivamente subdivide hasta convergencia. Sin dependencia externa.

### Bloque NORMALIZE (Fase 8) — detalle

Cinco ejercicios sobre escalado del Tema 5:

| Ejercicio | Endpoint | Fórmula |
|---|---|---|
| NORM-1 | `GET /api/preprolab/normalize/zscore/{tabla}/{columna}` | x' = (x - μ) / σ |
| NORM-2 | `GET /api/preprolab/normalize/minmax/{tabla}/{columna}` | x' = (x - min) / (max - min) |
| NORM-3 | `GET /api/preprolab/normalize/robust/{tabla}/{columna}` | x' = (x - mediana) / IQR |
| NORM-4 | `GET /api/preprolab/normalize/decimal/{tabla}/{columna}` | x' = x / 10^j |
| NORM-5 | `GET /api/preprolab/normalize/compare/{tabla}/{columna}` | aplica los 4 + tabla resumen + interpretación automática |

**Demo killer** sobre `sensors_readings.temperatura` (491 outliers de 1000°C inyectados en 98.440 filas):

| Método | min | max | std | % datos en [0, 0.1] |
|---|---|---|---|---|
| zscore | -0.36 | 13.92 | 1.0000 | 17% |
| **minmax** | 0.00 | 1.00 | 0.0700 | **99.5%** (catastrófico) |
| robust | -1.00 | 47.52 | 3.3975 | 5% (correcto) |
| decimal | 0.02 | 1.00 | 0.0686 | 99.5% |

Reproduce exactamente el ejemplo del PDF ("Min-Max con outliers comprime el 99% de los datos en una franja diminuta"). La interpretación automática lo señala: *"Min-Max comprime el 99.5% de los datos en el primer 10% del rango → hay outliers sesgando el escalado."*

### Bloque REDUCE_DIM (Fase 9) — detalle

Seis ejercicios sobre proyección + feature selection del Tema 5:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| REDDIM-1 | `GET /api/preprolab/reduce_dim/pca/robots?n_components=N` | PCA con autoselección (≥95% varianza) + scatter 2D coloreado por target |
| REDDIM-2 | `GET /api/preprolab/reduce_dim/tsne/robots?perplexity=P&max_rows=M` | t-SNE 2D (no lineal, visualización) |
| REDDIM-3 | `GET /api/preprolab/reduce_dim/filter/robots?method=chi2\|pearson\|variance\|mutual_info&k=N` | Filter univariate |
| REDDIM-4 | `GET /api/preprolab/reduce_dim/wrapper/robots?method=forward\|backward\|rfe&k=N` | Wrapper con RandomForest base |
| REDDIM-5 | `GET /api/preprolab/reduce_dim/embedded/robots?method=lasso\|rf_importance` | Embedded (Lasso L1 o RF importance) |
| REDDIM-6 | `GET /api/preprolab/reduce_dim/compare/robots?k=N` | Aplica las 3 familias + consenso |

AutoEncoders queda documentado en el PDF pero no implementado (requeriría PyTorch + entrenamiento costoso).

Validación end-to-end sobre `robots` con target `failure_next_48h`:

- **PCA auto**: 4 componentes explican 99.7% varianza (PC1=49.8% por las features altamente correlacionadas).
- **Filter mutual_info top 5**: `bateria_pct`, `battery_health_v2`, `consumo_total_kwh`, `voltaje_v`, `consumo_kw`.
- **RF importance top 5**: `battery_health_v2` (0.234), `voltaje_v` (0.193), `bateria_pct` (0.188), `consumo_total_kwh` (0.176), `consumo_kw` (0.170).
- **Compare**: **CONSENSO FUERTE** — las 3 familias (filter/wrapper/embedded) eligen las mismas 5 features. Solo `firmware_version` queda descartada por todas (score 0 en mutual info, importance 0.04 en RF). Esto demuestra que cuando las features son claramente informativas, los 3 métodos convergen al mismo resultado, lo que da confianza en la selección final.

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
