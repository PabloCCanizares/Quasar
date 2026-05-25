# Quasar

**Laboratorio Big Data + IA para la asignatura de Tratamiento y Gestión de Datos Masivos.**

Quasar es un **ecosistema multi-app** en el que cada aplicación demuestra un caso de uso distinto sobre la misma infraestructura común (MongoDB, Neo4j, Spark, FastAPI). Cada app se levanta de forma independiente, comparte el cluster poliglota y propone su propio conjunto de ejercicios scaffold/solución para el alumno.

El nombre evoca los **cuásares**: objetos cosmológicos extremadamente masivos y luminosos, alimentados por agujeros negros supermasivos. La metáfora encaja con la idea de procesar grandes volúmenes de datos para extraer información valiosa.

## Apps del ecosistema

| App | Estado | Puerto | Tema docente | Caso de uso |
|---|---|---|---|---|
| [**SocialLab**](apps/sociallab/) | Operativa | `:8000` | Bases poliglotas + Spark ML | Twitter falso con MongoDB + Neo4j + 6 modelos ML |
| [**PreproLab**](apps/preprolab/) | Esqueleto (Fase 1) | `:8002` | Tema 5 — Preprocesamiento | Flota de robots con mantenimiento predictivo, ~30 ejercicios |
| **LLM Lab** | Planificada | `:8001` | NLP / LLMs | Wikipedia ES + nanoGPT, demo de "limpieza → calidad del modelo" |

## Arquitectura

```
Quasar/
├── apps/
│   ├── sociallab/        ← Aplicación 1: red social poliglota
│   ├── preprolab/        ← Aplicación 2: preprocesamiento clásico (Tema 5)
│   └── llmprep/          ← Aplicación 3: limpieza de corpus + LLM (próximamente)
├── infra/
│   ├── shared/           ← Librerías Python comunes (config, mongo, neo4j, spark)
│   ├── compose/          ← docker-compose unificado + .env.docker
│   └── data/<app>/       ← Data lake por app (raw/silver/gold)
├── docs/                 ← Documentación técnica
├── notebooks/            ← Cuadernos pedagógicos
├── lab.sh                ← Orquestador: ./lab.sh <app> <comando>
└── slides.pdf            ← Slides del curso
```

**Infra compartida**: un solo MongoDB y un solo Neo4j para todo el ecosistema. Cada app tiene su propia base de datos (`sociallab`, `preprolab`, ...) y su propio data lake (`infra/data/<app>/`). Las apps web exponen sus propios puertos y son procesos independientes.

## Arranque rápido

Requisitos: Docker Desktop con Compose. Para modo nativo, además Python 3.11.

```bash
# Una app:
./lab.sh sociallab up exercises   # Arranca SocialLab + Mongo + Neo4j
./lab.sh sociallab seed           # Genera datos sucios
./lab.sh sociallab etl            # Spark ETL + carga MongoDB + Neo4j

# Otra app en paralelo (comparten Mongo + Neo4j):
./lab.sh preprolab up             # Arranca PreproLab :8002

# Ver qué está corriendo:
./lab.sh sociallab status
./lab.sh preprolab status

# Ayuda:
./lab.sh                          # Ayuda general
./lab.sh sociallab help           # Comandos de SocialLab
./lab.sh preprolab help           # Comandos de PreproLab
```

URLs:

- SocialLab: <http://localhost:8000>
- PreproLab: <http://localhost:8002>
- Neo4j browser: <http://localhost:7474> (credenciales `neo4j` / `neo4jneo4j`)
- Mongo: `mongodb://localhost:27017`

## Para quién es

- Estudiantes de **ingeniería de datos**, **Big Data** o **IA**.
- Profesores que quieran un laboratorio completo y ejecutable para enseñar arquitecturas modernas de datos.
- Desarrolladores curiosos sobre **Spark + MongoDB + Neo4j + FastAPI + ML** integrados.

Cada app representa una clase distinta de problema:

- **SocialLab** enseña por qué se usan bases poliglotas: la red social como caso natural (documental + grafo).
- **PreproLab** enseña el preprocesamiento como disciplina técnica completa (Tema 5 del temario).
- **LLM Lab** (cuando aterrice) enseñará cómo limpiar un corpus afecta directamente a la calidad del modelo entrenado.

## Patrón scaffold / solución

Todas las apps siguen el mismo patrón pedagógico:

- Cada algoritmo o bloque vive como **scaffold** (esqueleto con `raise NotImplementedError` o `exercise_placeholder`) y como **solución** (implementación oficial).
- Los flags `LAB_<APP>` controlan qué bloques están desbloqueados en runtime.
- El profesor "destapa" bloques según avance el curso con `./lab.sh <app> unlock <bloque>`.

Ver el README de cada app para los bloques disponibles y la lista detallada de ejercicios.

## Modo cloud

SocialLab soporta arranque cloud (MongoDB Atlas + Neo4j Aura free tier). Las otras apps lo soportarán de manera análoga. Ver [`docs/MIGRACION_CLOUD.md`](docs/MIGRACION_CLOUD.md) y [`apps/sociallab/README.md`](apps/sociallab/README.md).

## Documentación

- [`apps/sociallab/README.md`](apps/sociallab/README.md): SocialLab — ejercicios Cypher + ML, modo cloud, flujo completo.
- [`apps/preprolab/`](apps/preprolab/): PreproLab — en construcción.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): arquitectura técnica de SocialLab.
- [`docs/ARQUITECTURA_POLIGLOTA.md`](docs/ARQUITECTURA_POLIGLOTA.md): visión poliglota de datos.
- [`docs/MIGRACION_CLOUD.md`](docs/MIGRACION_CLOUD.md): migración a Atlas y Aura.

## Estructura de comandos `lab.sh`

```bash
./lab.sh <app> <comando> [args]
```

Apps reconocidas: `sociallab`, `preprolab`, `llmprep` (planificada).

Comandos comunes a todas las apps:

- `up [exercises|solutions]` — arranca la app + sus dependencias (mongo, neo4j)
- `down` / `stop` — para SOLO esta app (otras apps siguen corriendo)
- `status` — flags actuales y estado de los containers
- `logs` — sigue logs de la app
- `unlock <kind> <bloque>` / `lock <kind> <bloque>` — gestiona bloques
- `solutions` / `exercises` — toggle masivo
- `reset` — borra datos (pide confirmación)

Específicos de SocialLab:

- `seed` — genera datos sucios sintéticos
- `etl` — Spark raw → silver → gold → MongoDB + Neo4j
- `train` — entrena modelos ML según `LAB_ML`
- `cloud` / `cloud-down` — modo MongoDB Atlas + Neo4j Aura

Ver `./lab.sh <app> help` para detalles por app.

## Notas de desarrollo

- `.env`, `.env.cloud` y datos generados no se versionan.
- Cada app tiene su propio `.env` en `apps/<app>/.env` (modo nativo). El `.env.docker` compartido vive en `infra/compose/.env.docker`.
- Los data lakes (`infra/data/<app>/{raw,silver,gold}`) se regeneran con los comandos `seed` / `etl` / `train` de cada app.
- Las libs compartidas en `infra/shared/` (config, spark builder, mongo y neo4j helpers) son consumidas por todas las apps. Modifícalas con cuidado.
- Los cambios en `infra/shared/` y en `apps/<app>/src/` son **hot-reload** dentro del contenedor (bind mounts en compose). Solo `requirements.txt` o `Dockerfile` requieren rebuild.
