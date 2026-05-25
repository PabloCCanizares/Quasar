# PreproLab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.

**Laboratorio dedicado al Tema 5 del temario — Preprocesamiento clásico con Spark.**

PreproLab implementa todas las técnicas del temario sobre un dataset sintético construido a propósito: una **flota de robots autónomos con mantenimiento predictivo**. El escenario incluye intencionadamente los 10 tipos de problemas que el alumno tiene que resolver: valores perdidos (MCAR/MAR/MNAR), outliers de tres tipos, class noise, duplicados, fechas en formatos múltiples, encoding roto, multivaluadas, redundancia entre atributos, etc.

## Estado actual: Fase 1 (esqueleto)

Solo está montado el chasis del laboratorio. Los bloques se irán implementando en fases siguientes del roadmap Quasar.

| Bloque | Técnicas planificadas | Estado |
|---|---|---|
| `eda` | Univariable, bivariable, correlaciones, missing matrix | Fase 3 |
| `missing` | Diagnóstico MCAR/MAR/MNAR + Imputer (media/mediana), KNNI, KMI, MICE | Fase 4 |
| `outliers` | IQR, Z-score, boxplot + EF/CVCF/IPF noise filters | Fase 5 |
| `integration` | union, 4 tipos de joins, correlaciones para dedup | Fase 6 |
| `transform` | One-hot, ordinal, multi-flag, discretización (3 métodos), pivot/groupby | Fase 7 |
| `normalize` | Z-score, Min-Max, Robust, Decimal — comparados sobre mismo modelo | Fase 8 |
| `reduce_dim` | PCA, t-SNE, AutoEncoders + feature selection (filter/wrapper/embedded) | Fase 9 |
| `reduce_inst` | SRSWOR, estratificado, balanceado, K-Means compresión | Fase 10 |
| **Pipeline Studio** | UI para componer pipelines y comparar AUC/F1 sobre mismo modelo | Fase 11 |

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

## Dataset (Fase 2)

El generador construirá 4 tablas relacionadas:

- `robots` — id, modelo, fabricante, fecha_alta, almacén, ubicación, firmware
- `sensors_readings` — robot_id, timestamp, tipo, valor, batería, temperatura
- `events` — robot_id, timestamp, severidad, tipo, descripción
- `maintenances` — robot_id, fecha, tipo, duración, técnico, coste

Target: predicción de fallo en próximas 48h (clasificación binaria, RandomForest).

## API expuesta

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | `{"status": "ok", "app": "preprolab"}` |
| `GET /api/preprolab/lab/status` | Bloques desbloqueados según `LAB_PREPROLAB` |

Endpoints de cada bloque se añadirán según avancen las fases.
