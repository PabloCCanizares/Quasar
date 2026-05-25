# SocialLab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.

**Laboratorio Big Data para aprender bases de datos poliglotas con Spark, MongoDB, Neo4j y Machine Learning.**

SocialLab es un proyecto educativo y demostrativo para una asignatura de **Tratamiento de Datos Masivos**. Simula una red social completa para enseñar, de forma practica, como se diseña un ecosistema de datos moderno: **data lake**, **ETL con Spark**, **MongoDB**, **Neo4j**, **FastAPI**, visualizacion web y modelos de **Machine Learning**.

El proyecto esta pensado para que el estudiante entienda el recorrido completo del dato: desde datos crudos generados en un data lake local, pasando por transformaciones `raw -> silver -> gold` con Spark, hasta su explotacion en una **base de datos poliglota** donde cada motor cumple una funcion distinta. MongoDB se usa para documentos y consultas operacionales/analiticas, Neo4j para relaciones y recorridos de grafo, y los modelos ML consumen datos preparados en la capa gold.

Puede servir como caso de uso para docencia, demos tecnicas o aprendizaje autonomo sobre **arquitecturas Big Data**, **polyglot persistence**, **graph analytics**, **data engineering**, **Spark ETL**, **NoSQL** y **analitica aplicada a redes sociales**.

![Arquitectura de SocialLab](docs/assets/sociallab-architecture.png)

## Para quien es

- Estudiantes de ingenieria de datos, Big Data o sistemas de informacion.
- Profesores que quieran una practica completa y ejecutable con Docker.
- Desarrolladores que quieran ver un ejemplo integrado de **Spark + MongoDB + Neo4j**.
- Personas interesadas en bases de datos poliglotas, grafos sociales, NoSQL y pipelines ETL.

## Casos de uso del repositorio

- Practica universitaria de **Tratamiento de Datos Masivos**.
- Demo de **base de datos poliglota** con una parte documental y una parte de grafo.
- Proyecto de referencia para explicar un flujo **data lake -> Spark ETL -> MongoDB/Neo4j -> API -> dashboard**.
- Laboratorio para comparar consultas documentales, consultas Cypher y modelos ML sobre los mismos datos.
- Ejemplo de arquitectura local-first que puede migrarse despues a MongoDB Atlas, Neo4j Aura y plataformas cloud.

## Que se aprende

- Como se organiza un ecosistema de tratamiento de datos masivos de extremo a extremo.
- Como encaja un **data lake** por capas: raw, silver y gold.
- Como usar **Spark** como motor de ETL para limpiar, normalizar y agregar datos.
- Como diseñar una **base de datos poliglota**, combinando MongoDB y Neo4j segun el tipo de consulta.
- Como modelar una red social con usuarios, posts, likes, follows, hashtags e influencers.
- Como cargar datos analiticos en **MongoDB** y relaciones sociales en **Neo4j**.
- Como escribir consultas **Cypher** progresivas: basicas, intermedias y avanzadas.
- Como entrenar modelos de **ML** para spam, engagement, viralidad, churn, clustering y recomendacion.
- Como conectar todo con una aplicacion web que enseña el estado del laboratorio en tiempo real.

## Arquitectura

SocialLab se ejecuta localmente con Docker Compose y reproduce, en pequeno, una arquitectura habitual de tratamiento masivo de datos. La idea es que el estudiante vea el sistema como un conjunto conectado, no como tecnologias aisladas.

La arquitectura combina:

- **Data lake local** en `data/`, dividido en capas `raw`, `silver` y `gold`.
- **Spark ETL** para convertir datos sucios en datasets limpios y agregados.
- **MongoDB** como base documental para perfiles, publicaciones, interacciones y agregados listos para la web.
- **Neo4j** como base de datos de grafo para follows, comunidades, caminos, influencia y alcance.
- **ML Models** entrenados sobre datos gold para enriquecer la experiencia analitica.
- **FastAPI + Web UI** como capa de exposicion para explorar todo el ecosistema.

Esta combinacion forma una **base de datos poliglota**: no se fuerza todo en un unico motor, sino que cada tecnologia resuelve el tipo de problema para el que es mas natural.

Docker Compose arranca tres servicios principales:

| Servicio | Rol |
| --- | --- |
| `app` | FastAPI, frontend estatico, API REST, Spark local y entrenamiento ML |
| `mongodb` | Base documental para usuarios, posts, interacciones y agregados |
| `neo4j` | Grafo social para follows, comunidades, caminos e influencia |

El flujo de datos es:

1. `./lab.sh sociallab seed` genera datos sucios en `infra/data/sociallab/raw/`, simulando la ingesta inicial.
2. `./lab.sh sociallab etl` ejecuta Spark y transforma `raw -> silver -> gold`.
3. La capa `silver` normaliza entidades y relaciones.
4. La capa `gold` produce agregados y datasets listos para analitica y ML.
5. El ETL carga documentos en MongoDB y nodos/relaciones en Neo4j.
6. `./lab.sh sociallab train` entrena los modelos ML disponibles segun los flags del laboratorio.
7. La web en `http://localhost:8000` consume MongoDB, Neo4j y los artefactos ML.

## Base de datos poliglota

Una de las ideas principales de la practica es entender por que en sistemas de datos masivos no siempre se usa una unica base de datos. SocialLab separa responsabilidades:

| Capa | Tecnologia | Que aporta |
| --- | --- | --- |
| Data lake | Carpetas `data/raw`, `data/silver`, `data/gold` | Persistencia por capas y trazabilidad del proceso ETL |
| ETL | Spark | Limpieza, normalizacion, joins, agregaciones y preparacion analitica |
| Documental | MongoDB | Consulta flexible de usuarios, posts, timelines, perfiles y agregados |
| Grafo | Neo4j | Relaciones `FOLLOWS`, comunidades, caminos mas cortos, influencia y alcance |
| ML | scikit-learn + artefactos en `gold` | Modelos entrenados sobre datos preparados para enriquecer la aplicacion |
| API/UI | FastAPI + frontend | Punto de entrada para visualizar y probar el ecosistema completo |

El resultado es una arquitectura donde Spark prepara el dato, MongoDB resuelve la parte documental, Neo4j resuelve la parte relacional de grafo y la web permite observar el efecto de cada bloque implementado por el estudiante.

## Requisitos

- Docker Desktop con Docker Compose.
- Git.
- Python 3.11 si quieres ejecutar utilidades fuera del contenedor.

El flujo normal del estudiante no requiere instalar Spark, MongoDB ni Neo4j en local: viven dentro de Docker.

## Arranque rapido

```bash
./lab.sh sociallab up exercises
./lab.sh sociallab seed
./lab.sh sociallab etl
```

Despues abre:

- Web: `http://localhost:8000`
- Neo4j Browser: `http://localhost:7474`
- Credenciales Neo4j local: `neo4j / neo4jneo4j`

## Comandos principales

| Comando | Para que sirve |
| --- | --- |
| `./lab.sh sociallab up` | Arranca con la configuracion actual de `.env.docker` |
| `./lab.sh sociallab up exercises` | Arranca todo en modo scaffold |
| `./lab.sh sociallab up solutions` | Arranca con todos los bloques resueltos |
| `./lab.sh sociallab seed` | Genera datos sucios en `infra/data/sociallab/raw/` |
| `./lab.sh sociallab etl` | Ejecuta Spark, genera silver/gold y carga MongoDB + Neo4j |
| `./lab.sh sociallab train` | Entrena modelos ML segun `LAB_ML` |
| `./lab.sh sociallab status` | Muestra flags y estado de contenedores |
| `./lab.sh sociallab reset` | Borra volumenes y datos generados |
| `./lab.sh sociallab logs app` | Muestra logs del servicio `app` |

## Modo laboratorio

SocialLab usa flags en `.env.docker` para decidir si una parte se muestra como ejercicio o como solucion:

```env
LAB_NEO4J=
LAB_ML=
```

Bloques Neo4j:

- `basic`
- `intermediate`
- `advanced`

Bloques ML:

- `supervised`
- `unsupervised`
- `graph_ml`

Ejemplos:

```bash
./lab.sh sociallab unlock neo4j basic
./lab.sh sociallab unlock neo4j advanced
./lab.sh sociallab unlock ml supervised
./lab.sh sociallab lock ml supervised
```

Cuando se desbloquea un bloque de ML, el laboratorio reinicia la app y reentrena los modelos necesarios. Cuando un estudiante implementa ejercicios manualmente en Python, debe reiniciar la app para que FastAPI cargue el nuevo codigo:

```bash
docker compose restart app
```

## Itinerario de ejercicios

Los ejercicios estan organizados como un proyecto empresarial de datos: cada bloque representa una capacidad que una plataforma social real podria necesitar para analitica, producto, marketing, moderacion o crecimiento. El estudiante trabaja sobre ficheros scaffolded, implementa la logica y valida el resultado en una interfaz web.

El objetivo no es memorizar sintaxis aislada, sino entender como una decision tecnica termina apareciendo como una funcionalidad observable: un ranking, un radar, una recomendacion, una alerta de spam o una segmentacion de usuarios.

## Ejercicios Neo4j: analitica de grafo

Los ejercicios de Cypher estan en:

```text
src/web/routes/neo4j_basic_ex.py
src/web/routes/neo4j_intermediate_ex.py
src/web/routes/neo4j_advanced_ex.py
```

Cada endpoint representa una consulta de negocio sobre la red social. Las versiones resueltas equivalentes estan en `src/web/routes/neo4j_basic.py`, `src/web/routes/neo4j_intermediate.py` y `src/web/routes/neo4j_advanced.py`.

| Bloque | Ejercicio | Caso empresarial | Tecnicas trabajadas | Entregable visible |
| --- | --- | --- | --- | --- |
| Basic | `Neo4j-basic-1` Estadisticas del grafo | Cuadro ejecutivo del tamano de la red | `MATCH`, `count`, `WITH` | KPIs de usuarios, hashtags, follows e intereses |
| Basic | `Neo4j-basic-2` Top influencers | Identificar cuentas con mayor audiencia | Relaciones entrantes, agregacion, `ORDER BY`, `LIMIT` | Ranking de influencers |
| Basic | `Neo4j-basic-3` Comunidades por hashtag | Medir comunidades tematicas activas | Patrones `User -> Hashtag`, conteos por grupo | Lista de hashtags con mas usuarios |
| Intermediate | `Neo4j-intermediate-1` Usuarios puente | Detectar perfiles que conectan varias comunidades | `collect`, `DISTINCT`, filtros agregados | Usuarios con intereses diversos y seguidores |
| Intermediate | `Neo4j-intermediate-2` Intereses en comun | Buscar afinidad entre usuarios | Patron en V, hashtags compartidos | Recomendaciones por similitud tematica |
| Intermediate | `Neo4j-intermediate-3` Grafo de hashtags | Entender co-ocurrencia de intereses | Doble `MATCH`, pares sin duplicar, agregacion | Mapa de hashtags relacionados |
| Intermediate | `Neo4j-intermediate-4` Mis comunidades | Explicar a que grupos pertenece un usuario | Agrupacion por comunidad y miembros destacados | Panel de comunidades personales |
| Intermediate | `Neo4j-intermediate-5` Solapamiento social | Combinar afinidad tematica y relacion social | `OPTIONAL MATCH`, booleanos de follow | Tabla de overlap, `i_follow` y `follows_me` |
| Advanced | `Neo4j-advanced-1` Camino mas corto | Explicar la distancia social entre dos usuarios | `shortestPath`, caminos variables | Explorador de camino entre cuentas |
| Advanced | `Neo4j-advanced-2` Red ego | Visualizar el entorno cercano de un usuario | `FOLLOWS*1..N`, distancia minima, subgrafo | Grafo interactivo de red personal |
| Advanced | `Neo4j-advanced-3` Alcance entrante | Medir quien puede descubrirte por la red | Traversals por saltos, conteos acumulados | Radar de alcance a 1, 2 y 3 saltos |
| Advanced | `Neo4j-advanced-4` Distancia desde famosos | Medir proximidad a cuentas influyentes | `UNWIND`, `shortestPath`, `CASE WHEN` | Distancias desde influencers demo |

Al completar un ejercicio de Cypher:

```bash
docker compose restart app
```

Despues recarga la pestaña **Neo4j**. La validacion es visual: si el endpoint esta implementado, desaparece el mensaje de scaffold y aparece el ranking, grafo, radar o tabla correspondiente.

## Ejercicios ML: modelos analiticos

Los ejercicios de Machine Learning estan en:

```text
src/spark/models_ex/spam_detector.py
src/spark/models_ex/engagement_predictor.py
src/spark/models_ex/virality_classifier.py
src/spark/models_ex/churn_predictor.py
src/spark/models_ex/user_clustering.py
src/spark/models_ex/follow_recommender.py
```

Cada ejercicio consume datasets preparados en `infra/data/sociallab/gold/` por el ETL. El estudiante entrena modelos, guarda artefactos en `infra/data/sociallab/gold/models/` y expone metricas para que la web pueda mostrar si la solucion funciona.

| Bloque | Ejercicio | Caso empresarial | Tecnicas trabajadas | Entregable visible |
| --- | --- | --- | --- | --- |
| Supervised | `ML-supervised-1` Detector de spam | Moderacion y proteccion de la comunidad | Pipeline Spark ML, `VectorAssembler`, `StandardScaler`, Random Forest, AUC | Usuarios/posts sospechosos marcados cuando el modelo existe |
| Supervised | `ML-supervised-2` Prediccion de engagement | Estimar rendimiento esperado de contenidos | Feature engineering, regresion, evaluacion con RMSE/R2 | Predicciones de engagement para analitica de posts |
| Supervised | `ML-supervised-3` Clasificador de viralidad | Priorizar contenido con potencial de difusion | Clasificacion binaria, reutilizacion de features, metricas | Probabilidad/clase de contenido viral |
| Supervised | `ML-supervised-4` Predictor de churn | Detectar usuarios con riesgo de abandono | Construccion de features, clasificacion, precision/recall | Riesgo de churn por usuario |
| Unsupervised | `ML-unsupervised-1` Clustering de usuarios | Segmentacion de audiencia y perfiles de uso | KMeans, escalado, interpretacion de clusters | Segmentos de usuarios en la vista ML |
| Graph ML | `ML-graph_ml-1` Recomendador de follows | Crecimiento de red y recomendaciones sociales | Similitud, features de grafo, scoring | Sugerencias de a quien seguir |

Al completar un bloque de ML:

```bash
./lab.sh sociallab train
docker compose restart app
```

Despues recarga la pestaña **Spark/ML**. La validacion esperada es triple:

1. El comando `./lab.sh sociallab train` termina sin errores.
2. Aparecen metricas del modelo en la web.
3. La funcionalidad asociada se activa: spam marcado, predicciones, segmentos o recomendaciones.

## Datos demo

El seed incluye una red social sintetica con:

- Usuarios normales.
- Influencers inspirados en figuras reconocibles para demos docentes.
- Spammers para activar el detector de spam cuando el bloque ML correspondiente esta implementado.
- Posts, likes, follows, hashtags y relaciones suficientes para explorar comunidades, caminos e influencia.

En la web puedes buscar usuarios por username, explorar perfiles, ver timelines, analizar spam y navegar vistas Neo4j como resumen, influencers, comunidades, radar de alcance y camino mas corto.

## Estructura del proyecto

```text
SocialLab/
├── data/
│   ├── raw/                 # Datos crudos generados por seed
│   ├── silver/              # Datos limpios y normalizados
│   └── gold/                # Agregados y artefactos listos para analitica
├── docs/                    # Documentacion tecnica y diagramas
├── src/
│   ├── seed/                # Generacion de datos sinteticos
│   ├── spark/               # ETL y modelos ML
│   ├── web/                 # FastAPI, rutas, frontend y templates
│   └── models/              # Modelos de dominio
├── docker-compose.yml
├── Dockerfile
├── lab.sh
└── requirements.txt
```

## Flujo recomendado para estudiantes

```bash
./lab.sh sociallab up exercises
./lab.sh sociallab seed
./lab.sh sociallab etl
```

Despues:

1. Abrir la web y comprobar que aparecen los mensajes de ejercicios pendientes.
2. Implementar los ficheros `*_ex.py` o `models_ex/*.py`.
3. Reiniciar la app con `docker compose restart app`.
4. Ejecutar `./lab.sh sociallab train` si se han tocado ejercicios de ML.
5. Recargar la web y validar que el panel ya muestra resultados.

## Flujo recomendado para profesor

```bash
./lab.sh sociallab up exercises
./lab.sh sociallab seed
./lab.sh sociallab etl
./lab.sh sociallab unlock neo4j basic
./lab.sh sociallab unlock ml supervised
./lab.sh sociallab status
```

Tambien existe:

```bash
./lab.sh sociallab solutions
```

para destapar todos los bloques durante una demo.

## Modo cloud

El proyecto esta preparado para un modo ligero con MongoDB Atlas y Neo4j Aura:

```bash
cp .env.cloud.example .env.cloud
./lab.sh sociallab cloud
```

La guia completa esta en `docs/MIGRACION_CLOUD.md`.

## Documentacion adicional

- `docs/ARCHITECTURE.md`: arquitectura tecnica.
- `docs/ARQUITECTURA_POLIGLOTA.md`: vision poliglota de datos.
- `docs/MIGRACION_CLOUD.md`: migracion a Atlas y Aura.
- `src/web/routes/README_NEO4J_EJERCICIOS.md`: mapa de ejercicios Neo4j.
- `src/spark/models_ex/README.md`: mapa de ejercicios ML.

## Notas de desarrollo

- `.env`, `.env.cloud` y datos generados no se versionan.
- `data/raw`, `data/silver` y `data/gold` se regeneran con `seed`, `etl` y `train`.
- Los cambios en rutas FastAPI requieren reiniciar `app`.
- Los cambios en assets frontend pueden requerir recargar el navegador.
