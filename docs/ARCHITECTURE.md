# SocialLab — Arquitectura

## Principio rector

**Local primero, cloud después.** Migrar a cloud = cambiar `.env`, no reescribir código.

---

## 1. Estructura del proyecto

```
SocialLab/
├── .env.example          # Configuración con valores locales y comentarios cloud
├── src/
│   ├── config/           # config.py — pieza central, lee todo de .env
│   ├── web/              # FastAPI — API y frontend
│   ├── seed/             # Generación de datos iniciales (agentes, posts, etc.)
│   ├── graph/            # Operaciones Neo4j (relaciones sociales)
│   ├── spark/            # Jobs Spark (transformaciones raw→silver→gold)
│   └── models/           # Modelos Pydantic compartidos
├── data/
│   ├── raw/              # Datos crudos (JSON, CSV de seed o ingestión)
│   ├── silver/           # Datos limpios y normalizados
│   └── gold/             # Datos agregados listos para consumo
├── tests/
└── docs/
```

---

## 2. Data Lake — Carpetas locales

No hay MinIO ni S3 en local. El data lake son directorios en disco.

| Capa   | Ruta local       | Ruta cloud (Databricks)                        |
|--------|------------------|-------------------------------------------------|
| Raw    | `./data/raw/`    | `dbfs:/mnt/sociallab/raw/` o `abfss://...`      |
| Silver | `./data/silver/` | `dbfs:/mnt/sociallab/silver/`                   |
| Gold   | `./data/gold/`   | `dbfs:/mnt/sociallab/gold/`                     |

La variable `DATA_LAKE_PATH` en `.env` controla la raíz. Todo el código usa `config.DATA_LAKE_PATH` — nunca rutas hardcodeadas.

**Migración:** Cambiar `DATA_LAKE_PATH=./data` → `DATA_LAKE_PATH=/dbfs/mnt/sociallab`.

---

## 3. MongoDB — Una colección por entidad

### Diseño

Cada entidad tiene **una sola colección**. El campo `origin` distingue el origen de los datos:

```json
{
  "_id": "agent_001",
  "name": "María García",
  "origin": "seed",
  "personality": { ... },
  "created_at": "2026-03-29T10:00:00Z"
}
```

| `origin`  | Significado                        |
|-----------|------------------------------------|
| `seed`    | Generado por el proceso de seed    |
| `live`    | Creado durante la simulación       |
| `import`  | Importado de fuente externa        |

### Colecciones principales

| Colección    | Descripción                          |
|--------------|--------------------------------------|
| `agents`     | Perfiles de agentes sociales         |
| `posts`      | Publicaciones generadas              |
| `interactions` | Likes, comentarios, shares         |
| `simulations`| Configuración y estado de simulaciones|

### Migración a Atlas

Cambiar `MONGO_URI` en `.env`:

```
# Local
MONGO_URI=mongodb://localhost:27017

# Atlas
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net
```

El código no cambia. `pymongo` y `motor` soportan ambos esquemas de URI.

---

## 4. Neo4j — Grafo social

Neo4j almacena las relaciones entre agentes: follows, menciones, influencia.

### Nodos y relaciones

```
(:Agent {id, name})
(:Agent)-[:FOLLOWS]->(:Agent)
(:Agent)-[:MENTIONED {post_id}]->(:Agent)
(:Agent)-[:INFLUENCED_BY {weight}]->(:Agent)
```

### Migración a Aura

```
# Local
NEO4J_URI=bolt://localhost:7687

# Aura
NEO4J_URI=neo4j+s://abc123.databases.neo4j.io
```

El driver `neo4j` de Python soporta ambos esquemas.

---

## 5. Spark — Preparado para Databricks

### Principio

Cada job de Spark es una **función pura** que recibe:
1. Una `SparkSession`
2. Rutas de entrada/salida como parámetros

```python
def transform_posts(spark: SparkSession, input_path: str, output_path: str):
    df = spark.read.json(input_path)
    # transformaciones...
    df.write.parquet(output_path, mode="overwrite")
```

### Ejecución local

```python
from pyspark.sql import SparkSession
from src.config import SPARK_MASTER, RAW_PATH, SILVER_PATH

spark = SparkSession.builder.master(SPARK_MASTER).appName("sociallab").getOrCreate()
transform_posts(spark, str(RAW_PATH / "posts"), str(SILVER_PATH / "posts"))
```

### Ejecución en Databricks

```python
# En un notebook de Databricks — spark ya existe
transform_posts(spark, "/mnt/sociallab/raw/posts", "/mnt/sociallab/silver/posts")
```

**El mismo código.** Databricks provee `spark`. Las rutas vienen de la config (o del notebook).

---

## 6. config.py — Pieza central

```
.env  →  config.py  →  toda la app
```

`src/config/__init__.py` carga `.env` con `python-dotenv` y expone constantes tipadas. Cualquier módulo importa:

```python
from src.config import MONGO_URI, NEO4J_URI, DATA_LAKE_PATH
```

**Regla:** si algo puede cambiar entre local y cloud, va en `.env` y se lee desde `config`.

---

## 7. Stack tecnológico

| Componente     | Local                  | Cloud                     |
|----------------|------------------------|---------------------------|
| Web/API        | FastAPI + Uvicorn      | FastAPI (App Service/ECS) |
| Base de datos  | MongoDB Community      | MongoDB Atlas             |
| Grafo          | Neo4j Community        | Neo4j Aura                |
| Data Lake      | Carpetas locales       | DBFS / ADLS / S3          |
| Procesamiento  | PySpark local          | Databricks                |
| Config         | `.env` local           | Variables de entorno      |

---

## 8. Plan de implementación

| Día   | Objetivo                                    | Entregable                          |
|-------|---------------------------------------------|-------------------------------------|
| 1-2   | Web + MongoDB funcionando                   | API CRUD de agentes, web sirviendo  |
| 3     | Seed + Neo4j                                | Datos iniciales + grafo social      |
| 4     | Spark pipelines                             | raw → silver → gold funcionando     |
| 5     | Verificar portabilidad cloud                | Migración a Atlas/Aura sin tocar código |

---

## 9. Convenciones

- **Nombres de colecciones:** plural, snake_case (`agents`, `posts`, `interactions`)
- **Campo `origin`:** siempre presente en todo documento MongoDB
- **Rutas de datos:** siempre vía `config`, nunca hardcodeadas
- **Spark jobs:** funciones puras, sin efectos laterales fuera de lectura/escritura
- **Tests:** en `tests/`, espejo de `src/` (`tests/test_web/`, `tests/test_seed/`, etc.)
