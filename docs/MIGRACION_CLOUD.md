# Guía de migración — SocialLab local → Cloud **100% gratuito**

Pasos concretos para pasar de stack local a un entorno cloud con tres
servicios, **todos en plan gratuito**:

- **MongoDB Atlas M0** (Free Forever — 512 MB)
- **Neo4j AuraDB Free** (200 000 nodos / 400 000 relaciones)
- **Databricks Community Edition** (single-node, sin tarjeta de crédito)

Tiempo estimado de provisionado: ~45 minutos. Coste: **0 €**.

> Diferencias clave frente a la versión de pago:
> - Databricks Community Edition (CE) **no incluye** Unity Catalog, Secret
>   Scopes ni Jobs/Workflows. Trabajaremos con DBFS clásico, variables de
>   notebook y ejecución manual encadenada con `%run`.
> - Atlas M0 y Aura Free son monoinstancia y comparten recursos: vale
>   sobradamente para el dataset de SocialLab (~95 000 relaciones,
>   ~2 600 usuarios) pero no para producción.
> - El CLI de Databricks **no funciona** contra CE; subiremos datos por la
>   UI o con `wget` desde dentro de un notebook.

---

## ¿Encaja el dataset en los límites free?

| Recurso             | Límite free                  | Dataset SocialLab actual         | Margen      |
|---------------------|------------------------------|----------------------------------|-------------|
| Atlas M0 storage    | 512 MB                       | ~300 MB (Mongo + índices)        | OK justo    |
| Aura Free nodos     | 200 000                      | ~10 500 (users + hashtags)       | 5 % usado   |
| Aura Free relaciones| 400 000                      | ~95 000 (FOLLOWS + INTERESTED_IN)| 24 % usado  |
| Databricks CE RAM   | ~6 GB driver                 | ETL completo cabe                | OK          |
| Databricks CE disco | ~15 GB driver                | Lake completo (~600 MB)          | OK          |

---

## Fase 0 — Checklist previa

- [ ] `./start.sh all` (o `./lab.sh up solutions && ./lab.sh seed && ./lab.sh etl`) funciona en local.
- [ ] `data/raw/` contiene los NDJSON (~50 MB).
- [ ] Crear cuenta gratuita en cada servicio:
  - MongoDB Atlas: <https://www.mongodb.com/cloud/atlas/register>
  - Neo4j Aura: <https://console.neo4j.io/?signup>
  - Databricks Community Edition: <https://community.cloud.databricks.com/login.html>
    (asegúrate de pulsar **"Get started with Community Edition"**, NO el
    botón principal que pide tarjeta).
- [ ] Crear `.env.cloud` a partir de `.env.example` (lo iremos rellenando).

---

## Fase 1 — Data Lake en DBFS (Databricks CE)

**Objetivo:** carpeta `dbfs:/FileStore/sociallab/{raw,silver,gold}` accesible
desde cualquier notebook del workspace.

En Community Edition **no existe** Unity Catalog, así que usamos DBFS
clásico bajo `FileStore` (es la única ruta que la UI permite mostrar y
sobre la que se pueden subir ficheros).

Esta fase se ejecuta una vez creado el workspace (Fase 4). Vuelve aquí
después de la Fase 4.

### 1.1 Crear las carpetas

Desde un notebook Python en el workspace:

```python
for layer in ("raw", "silver", "gold"):
    dbutils.fs.mkdirs(f"dbfs:/FileStore/sociallab/{layer}")
display(dbutils.fs.ls("dbfs:/FileStore/sociallab/"))
```

### 1.2 Anotar en `.env.cloud`

```env
DATA_LAKE_PATH=dbfs:/FileStore/sociallab
```

> Nota: Community Edition borra DBFS si la cuenta queda inactiva muchos
> meses. Para una clase de 1 cuatrimestre no es problema.

---

## Fase 2 — MongoDB Atlas (M0 free)

**Objetivo:** cluster M0 con un usuario `sociallab_app` (rw) y otro
`sociallab_ro` (read-only para los alumnos).

### 2.1 Crear proyecto y cluster M0

1. <https://cloud.mongodb.com> → **New Project** `SocialLab`.
2. **Build a Database** → escoger **M0 (Shared, Free Forever)**.
3. Provider y región: cualquiera próxima (p. ej. AWS · Frankfurt).
4. Nombre del cluster: `sociallab-cluster` → **Create**.

Esperar ~3 minutos a que aparezca **Active**.

> Atlas free permite **un solo cluster M0 por proyecto** y un proyecto por
> cuenta gratuita. Para clase: el profesor monta uno y los alumnos se
> conectan con usuario read-only.

### 2.2 Crear usuarios de base de datos

**Database Access → Add New Database User** (password):

| Usuario          | Rol                                          |
|------------------|----------------------------------------------|
| `sociallab_app`  | `readWrite` en DB `sociallab`                |
| `sociallab_ro`   | `read` en DB `sociallab` (para alumnos)      |

> En M0 no hace falta `sociallab_etl` separado: Databricks puede
> escribir con `sociallab_app` (es solo durante la práctica).

### 2.3 Network Access

**Network Access → Add IP Address → Allow Access from Anywhere**
(`0.0.0.0/0`). En cluster M0 esto es lo más práctico durante la clase
porque Databricks Community no expone una IP fija.

> En entorno productivo nunca usaríamos `0.0.0.0/0`. Aquí es aceptable
> porque M0 no contiene datos sensibles y es un dataset sintético.

### 2.4 Connection string

**Database → Connect → Drivers → Python 3.11+**: copiar URI.

```env
# .env.cloud
MONGO_URI=mongodb+srv://sociallab_app:<pwd>@sociallab-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB=sociallab
```

### 2.5 Validar desde el portátil

```bash
python -c "from pymongo import MongoClient; import os; \
from dotenv import load_dotenv; load_dotenv('.env.cloud'); \
print(MongoClient(os.environ['MONGO_URI']).list_database_names())"
```

---

## Fase 3 — Neo4j AuraDB Free

**Objetivo:** instancia gratuita `sociallab-graph` con constraints.

### 3.1 Crear instancia

1. <https://console.neo4j.io> → **New Instance**.
2. Seleccionar **AuraDB Free** (no Professional).
3. Región europea cercana → nombre `sociallab-graph` → **Create**.
4. **Descargar el fichero de credenciales** (solo se muestra una vez)
   contiene URI `neo4j+s://...` y password generado.

> Aura Free se **pausa automáticamente tras 3 días sin queries** y se
> reanuda al primer acceso (~30 s de espera la primera vez). Si vuestra
> clase tiene gaps largos, la primera consulta del día puede tardar.

### 3.2 Crear constraints

Abrir **Neo4j Browser** desde la consola y ejecutar:

```cypher
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
  FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT hashtag_name_unique IF NOT EXISTS
  FOR (h:Hashtag) REQUIRE h.name IS UNIQUE;
```

### 3.3 Anotar en `.env.cloud`

```env
NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password del fichero descargado>
```

### 3.4 Validar

```bash
python -c "from neo4j import GraphDatabase; import os; \
from dotenv import load_dotenv; load_dotenv('.env.cloud'); \
d = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])); \
d.verify_connectivity(); print('OK')"
```

---

## Fase 4 — Databricks Community Edition

**Objetivo:** workspace con un cluster single-node, conectores Mongo/Neo4j
instalados y notebooks importados.

### 4.1 Crear cuenta y entrar al workspace

1. <https://community.cloud.databricks.com/login.html> → **Sign Up**.
2. Email + datos básicos. **Cuidado**: hay dos botones de signup en la
   web; debe ser explícitamente **"Get started with Community Edition"**.
   Si te pide tarjeta de crédito has caído en el plan de prueba normal.
3. Verifica el correo y entra al workspace.

> CE no tiene CLI ni REST API completa: todo se hace desde la UI web.
> Tampoco tiene Secret Scopes — pasaremos credenciales como variables de
> notebook (widgets) o leyendo un archivo subido a DBFS.

### 4.2 Crear cluster

UI → **Compute** → **Create Cluster**:

| Campo            | Valor                                          |
|------------------|------------------------------------------------|
| Cluster name     | `sociallab`                                    |
| Databricks Runtime | **15.4 LTS** (o la última LTS con Spark 3.5+) |
| Worker type      | (no aplica — CE es single-node)                |
| Driver type      | Default (Community Edition asigna uno)         |
| Terminate after  | 120 min (no editable en CE)                    |

Pulsa **Create cluster** y espera ~5 min a estado **Running**.

> Limitaciones de CE: el cluster **se apaga solo tras ~2 h** de inactividad
> y **borra el estado del driver al apagarse**. DBFS persiste, pero los
> JARs de librerías hay que reinstalarlos al rearrancar el cluster.

### 4.3 Instalar conectores Maven

Cluster → pestaña **Libraries → Install new → Maven**, instalar uno por uno:

- `org.mongodb.spark:mongo-spark-connector_2.12:10.4.0`
- `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`

Esperar a estado **Installed** en cada uno (~1 min cada uno). Reiniciar
el cluster si la UI lo pide.

### 4.4 Crear las carpetas DBFS (Fase 1)

Crear un notebook nuevo (botón **+ New → Notebook**, lenguaje Python,
asociarlo al cluster `sociallab`) y ejecutar:

```python
for layer in ("raw", "silver", "gold"):
    dbutils.fs.mkdirs(f"dbfs:/FileStore/sociallab/{layer}")
display(dbutils.fs.ls("dbfs:/FileStore/sociallab/"))
```

### 4.5 Importar el código del repo como notebooks

Sin CLI no podemos hacer `import-dir`. Dos opciones:

**Opción A — Subir desde la UI (recomendado para clase)**

1. Workspace → carpeta personal (`/Users/<tu-email>/`) → menú **▾ Create → Folder** → `sociallab`.
2. Dentro de la carpeta: **▾ Create → File** y arrastrar uno a uno los `.py` desde `src/spark/`:
   - `etl_silver.py`
   - `etl_gold.py`
   - `load_to_mongo.py`
   - `load_to_neo4j.py`
3. Para cada archivo, abrirlo y **File → Convert to Notebook**.

**Opción B — Clonar el repo desde un notebook**

```python
%sh
cd /tmp && git clone https://github.com/<tu-fork>/SocialLab.git
ls SocialLab/src/spark/
```

Después referenciar los `.py` con `%run /tmp/SocialLab/src/spark/etl_silver.py`
desde un notebook orquestador.

### 4.6 Adaptar los scripts para Databricks

En cada notebook, sustituir la inicialización local por las versiones que
usan el `spark` global del notebook y leen credenciales de variables del
notebook (no hay Secret Scopes en CE).

```python
# Antes (local):
# from dotenv import load_dotenv; load_dotenv()
# from pyspark.sql import SparkSession
# spark = SparkSession.builder.master("local[*]").getOrCreate()

# Después (Databricks CE):
dbutils.widgets.text("MONGO_URI",       "")
dbutils.widgets.text("NEO4J_URI",       "")
dbutils.widgets.text("NEO4J_PASSWORD",  "")

MONGO_URI       = dbutils.widgets.get("MONGO_URI")
NEO4J_URI       = dbutils.widgets.get("NEO4J_URI")
NEO4J_USER      = "neo4j"
NEO4J_PASSWORD  = dbutils.widgets.get("NEO4J_PASSWORD")
DATA_LAKE_PATH  = "dbfs:/FileStore/sociallab"
```

> Cuando ejecutes el notebook, Databricks pintará los widgets arriba.
> Pega ahí los valores de `.env.cloud`. Es menos seguro que los Secret
> Scopes pero es la única opción en CE.

### 4.7 Notebook orquestador (sustituye al Workflow)

Como CE no tiene Jobs/Workflows, montamos un notebook que ejecuta los
demás en cadena:

```python
# 00_run_all.py
%run ./etl_silver
%run ./etl_gold
%run ./load_to_mongo
%run ./load_to_neo4j
```

Ejecútalo manualmente desde la UI cuando quieras pasar el ETL completo.

---

## Fase 5 — Subir datos al lake (sin CLI)

### 5.1 Generar datos sucios en local

```bash
./start.sh seed    # genera data/raw/*.json (~50 MB)
```

### 5.2 Subir al DBFS de Databricks CE

CE no permite `databricks fs cp`. Tres alternativas:

**A — UI directa (la más simple para 4 ficheros)**

1. Workspace UI → menú **Catalog → Browse DBFS** (si no aparece, activarlo
   en User Settings → Workspace settings → DBFS File Browser).
2. Navegar a `FileStore/sociallab/raw/`.
3. **Upload** y seleccionar `users.json`, `posts.json`, `likes.json`, `follows.json`.

**B — Desde un notebook con `requests` (si publicas el dataset)**

Empaqueta los 4 NDJSON en un `tar.gz`, súbelo como release de tu repo
GitHub, y desde un notebook:

```python
%sh
cd /dbfs/FileStore/sociallab/raw && \
wget -q https://github.com/<tu-fork>/SocialLab/releases/download/v1/raw.tar.gz && \
tar xzf raw.tar.gz && rm raw.tar.gz && ls -lh
```

**C — Regenerar dentro del notebook**

Importa también `src/seed/generate_dirty_data.py` como notebook y
ejecútalo cambiando `RAW_PATH` al path DBFS:

```python
RAW_PATH = "/dbfs/FileStore/sociallab/raw"
# y al final escribir con open(...) normal — DBFS está montado en /dbfs/
```

Esta opción evita subir nada manualmente.

### 5.3 Verificar

```python
display(dbutils.fs.ls("dbfs:/FileStore/sociallab/raw"))
# debe listar users.json, posts.json, likes.json, follows.json
```

### 5.4 Ejecutar el pipeline

Abrir el notebook orquestador `00_run_all` (Fase 4.7), pegar los valores
de `.env.cloud` en los widgets de cada notebook hijo (o usar globales),
y pulsar **Run all**.

Duración esperada: **15–20 min** (CE es single-node, va mucho más lento
que un cluster Premium).

### 5.5 Verificar Atlas y Aura

```bash
# Atlas — contar documentos por colección
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; \
load_dotenv('.env.cloud'); db = MongoClient(os.environ['MONGO_URI'])[os.environ['MONGO_DB']]; \
[print(c, db[c].count_documents({})) for c in ['users','posts','likes','follows']]"

# Aura — contar nodos
python -c "from neo4j import GraphDatabase; import os; from dotenv import load_dotenv; \
load_dotenv('.env.cloud'); d = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=('neo4j', os.environ['NEO4J_PASSWORD'])); \
s = d.session(); print(s.run('MATCH (u:User) RETURN count(u)').single())"
```

---

## Fase 6 — FastAPI local contra cloud

La capa web sigue corriendo en el portátil del usuario. Solo cambia `.env`.

### 6.1 Activar `.env.cloud`

```bash
cp .env .env.local.bak       # backup del modo local
cp .env.cloud .env           # activar modo cloud
```

### 6.2 Arrancar API

```bash
./start.sh web
```

### 6.3 Probar

- <http://localhost:8000> → SPA carga usuarios desde Atlas.
- Crear un post → aparece con `origin: "live"` en Atlas.
- Pestaña Neo4j → consulta Aura.

> Los flags `LAB_NEO4J` y `LAB_ML` (sistema scaffold/solution) **funcionan
> exactamente igual** en cloud: son variables de entorno de la app, no
> dependen de dónde estén las BBDD. Define en `.env.cloud`:
> ```
> LAB_NEO4J=
> LAB_ML=
> ```
> y ve "destapando" bloques con `./lab.sh unlock neo4j basic` (si usas
> Docker) o editando `.env` a mano (si usas el modo nativo).

---

## Fase 7 — Reparto a alumnos (todo gratis)

Tres modelos, de menos a más autónomo. Elige el que encaje con tu clase.

### Modelo A — Atlas + Aura compartidos por el profesor (recomendado)

El profesor mantiene **una sola** instancia de cada servicio. Los
alumnos solo necesitan acceso de lectura. Es la opción más sencilla y la
única que permite que todos vean los mismos datos.

Entregables al alumno:
1. **Repo SocialLab** (tag `cloud-ready`).
2. **Plantilla `.env.alumno`**:
   ```env
   MONGO_URI=mongodb+srv://sociallab_ro:<pwd>@sociallab-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   MONGO_DB=sociallab
   NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<pwd-readonly-de-aura>
   DATA_LAKE_PATH=./data
   SPARK_MASTER=local[*]
   WEB_HOST=0.0.0.0
   WEB_PORT=8000
   WEB_DEBUG=true
   ENV=cloud
   LAB_NEO4J=
   LAB_ML=
   ```
3. (Opcional) Invitación a tu workspace de Databricks Community con un
   notebook con permiso de lectura. **Atención**: CE comparte workspace
   solo si el alumno entra con tu URL — no hay control de permisos. Si
   quieres aislamiento, ve al **Modelo B**.

> Aura Free no tiene usuarios read-only. Crea una cuenta dedicada al
> alumnado o reparte el password de la cuenta principal aceptando que
> pueden escribir.

### Modelo B — Cada alumno con sus propias cuentas free

Cada alumno crea su propio Atlas M0, su propia Aura Free y su propia
Databricks Community. Cero coste, total aislamiento, pero cada uno tiene
que pasar por las Fases 0-5 él mismo. Útil si quieres que la propia
infra sea parte del ejercicio.

Tiempo de setup por alumno: **~45 min** la primera vez.

### Modelo C — Solo Aura para el bloque Cypher

Si quieres limitar el coste cognitivo en clases breves (p. ej. una
sesión sobre Cypher avanzado), basta con que cada alumno cree **solo**
una instancia Aura Free y trabaje sobre el grafo desde Neo4j Browser
+ los notebooks de prácticas. Sin Atlas ni Databricks. Las pestañas
de la app FastAPI no se usan en este modelo.

### Sobre los scaffolds en cloud

El sistema scaffold/solution **funciona transparentemente en cloud**:
los flags `LAB_NEO4J` y `LAB_ML` viven en el `.env` de la app FastAPI,
no en las bases de datos. Aunque Mongo y Neo4j estén en Atlas/Aura, la
app sigue cargando `neo4j_basic_ex.py` o `neo4j_basic.py` según el
flag.

Para los notebooks Spark (la versión Databricks de los modelos ML),
distribuye al alumno los archivos del directorio `src/spark/models_ex/`
en vez de los de `src/spark/models/`. Cuando el alumno termine un
ejercicio, el profesor sustituye el notebook correspondiente por la
versión solución en su carpeta personal de Databricks.

---

## Fase 8 — Apagado / pausa

| Servicio              | Coste residual | Acción                              |
|-----------------------|----------------|-------------------------------------|
| Atlas M0              | 0 €            | Nada — siempre on, no factura.      |
| Aura Free             | 0 €            | Se pausa solo a los 3 días.         |
| Databricks CE cluster | 0 €            | Se apaga solo a las 2 h. Driver borra estado, pero DBFS persiste. |
| Databricks CE workspace | 0 €          | Eliminar cuenta si ya no se usa.    |

**No hay nada que apagar manualmente para evitar facturación: ningún
servicio cobra.** El único riesgo es perder datos si la cuenta queda
inactiva muchísimos meses (Atlas y Aura purgan eventualmente cuentas
inactivas — Atlas avisa por email).

---

## Limitaciones conocidas del modo free

| Servicio          | Limitación                              | Impacto en SocialLab |
|-------------------|-----------------------------------------|----------------------|
| Atlas M0          | 512 MB storage                          | OK justo (~300 MB usados); si añades más datos sintéticos puede saturar |
| Atlas M0          | Conexión compartida con otros usuarios  | Latencia variable, queries lentas en hora punta |
| Aura Free         | Auto-pausa tras 3 días                  | Primera query del día tarda ~30 s |
| Aura Free         | 200k nodos / 400k relaciones            | Margen amplio actualmente |
| Aura Free         | Sin backup ni point-in-time recovery    | Si se borra, hay que regenerar desde el ETL |
| Databricks CE     | Cluster se apaga solo a las 2 h         | Hay que reinstalar Maven al rearrancar |
| Databricks CE     | Sin CLI, sin REST API completa          | Todo manual desde la UI |
| Databricks CE     | Sin Secret Scopes                       | Credenciales como widgets de notebook (menos seguro) |
| Databricks CE     | Sin Jobs/Workflows                      | Encadenar notebooks con `%run` y ejecutar a mano |
| Databricks CE     | Single-node ~6 GB RAM                   | ETL tarda 15–20 min vs 8–12 min en Premium |
| Databricks CE     | Solo Python/SQL (no Scala job clusters) | No nos afecta — usamos PySpark |

---

## Troubleshooting rápido

| Síntoma                                        | Causa probable                           | Solución                                          |
|------------------------------------------------|------------------------------------------|---------------------------------------------------|
| `MongoSocketOpenException` en Atlas            | IP no está en allowlist                  | Network Access → `0.0.0.0/0` (en clase es aceptable) |
| Atlas M0: "command failed with: storage limit exceeded" | Has llenado los 512 MB           | Vacía colecciones grandes o sube a M2 (de pago)   |
| `ServiceUnavailable` en Aura                   | Instancia pausada por inactividad        | La primera query la reanuda (~30 s)               |
| Aura: "Database limit exceeded"                | >200k nodos                              | Reduce el dataset (NUM_USERS / NUM_POSTS en seed) |
| Databricks notebook falla con `py4j.Py4JException` | Conector Maven no instalado o cluster reiniciado | Reinstalar libraries en pestaña Libraries del cluster |
| Databricks `%run` no encuentra el notebook     | Path incorrecto en CE                    | Usa rutas absolutas: `%run /Users/<email>/sociallab/etl_silver` |
| Notebook tarda muchísimo en CE                 | Cluster recién arrancado y JARs descargándose | Espera 2-3 min al primer run; luego es cache hit |
| `dbutils.widgets.get(...)` devuelve string vacío | Olvidaste pegar el valor en la cabecera del notebook | Pega los valores de `.env.cloud` en cada widget    |
| Spam no filtrado en silver                     | Lógica depende de timezone               | Revisar UDF `parse_timestamp` en `etl_silver`     |

---

## Resumen ejecutivo

| Servicio                | Plan free                | Setup     | Mantenimiento mensual |
|-------------------------|--------------------------|-----------|------------------------|
| MongoDB Atlas           | M0 Shared (512 MB)       | ~5 min    | 0 €                   |
| Neo4j AuraDB            | Free (200k nodos)        | ~5 min    | 0 €                   |
| Databricks              | Community Edition        | ~10 min   | 0 €                   |
| FastAPI (alumno)        | Local en su portátil     | ~2 min    | 0 €                   |
| **TOTAL**               |                          | **~22 min** + datos | **0 €**          |

El compromiso real del plan free no es el coste sino la **velocidad** y
la **conveniencia**: ETL más lento (single-node), credenciales menos
seguras (sin Secret Scopes), sin orquestación automatizada (sin Jobs).
A cambio, la práctica completa funciona sin que ningún alumno tenga
que dar tarjeta de crédito.
