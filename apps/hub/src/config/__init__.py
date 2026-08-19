"""Quasar Hub — configuración y catálogo del ecosistema.

Fuente única de verdad para el Hub: qué apps hay, qué bloques tiene cada
una (con etiquetas legibles + descripción + nº de ejercicios), cómo
alcanzarlas, qué contenedor reiniciar, qué comandos operativos exponen
(seed/etl) y qué enlaces útiles ofrecer.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_APP_ROOT = Path(__file__).resolve().parent.parent.parent
_LOCAL_ENV = _APP_ROOT / ".env"
if _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV)

WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))
WEB_DEBUG: bool = os.getenv("WEB_DEBUG", "true").lower() == "true"

# Archivo de flags que el Hub edita (montado desde infra/compose/.env.docker).
ENV_FILE: str = os.getenv("QUASAR_ENV_FILE", "/quasar/.env.docker")

# Data lake montado read-only para comprobar si hay datos generados.
DATA_ROOT: str = os.getenv("QUASAR_DATA_ROOT", "/quasar/data")

# URIs de infraestructura (red interna del compose).
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
NEO4J_HOST = os.getenv("NEO4J_HOST", "neo4j")
NEO4J_BOLT_PORT = int(os.getenv("NEO4J_BOLT_PORT", "7687"))
NEO4J_HTTP_PORT = int(os.getenv("NEO4J_HTTP_PORT", "7474"))


# ============================================================
# Catálogo de apps
# ============================================================
# Cada bloque: {flag, key, label, desc, exercises}. El `key` es el id
# dentro de su flag; `flag` la variable LAB_* que lo controla.

APPS = {
    "sociallab": {
        "name": "SocialLab",
        "tagline": "Red social poliglota",
        "description": "Bases de datos poliglotas (MongoDB + Neo4j), ETL con Spark, grafos sociales y modelos de Machine Learning sobre una red social sintética.",
        "url_internal": "http://app-sociallab:8000",
        "url_public": "http://localhost:8000",
        "container": "quasar-sociallab",
        "status_path": "/api/analytics/lab/status",
        "docs": "http://localhost:8000/docs",
        "readme": "https://github.com/PabloCCanizares/Quasar/blob/main/apps/sociallab/README.md",
        "color": "#1da1f2",
        "tech": ["MongoDB", "Neo4j", "Spark MLlib", "Cypher", "FastAPI"],
        "architecture": [
            {"label": "Seed", "sub": "datos sucios sintéticos"},
            {"label": "Spark ETL", "sub": "raw → silver → gold"},
            {"split": [
                {"label": "MongoDB", "sub": "users · posts · likes"},
                {"label": "Neo4j", "sub": "FOLLOWS · INTERESTED_IN"},
            ]},
            {"label": "FastAPI + Web", "sub": "timeline · grafo · ML (spam, churn…)"},
        ],
        "tasks": {
            "seed": "Generar datos sucios",
            "etl": "ETL Spark → Mongo + Neo4j",
            "train": "Entrenar modelos ML",
        },
        "uses_neo4j": True,
        "uses_mongo": True,
        "blocks": [
            {"flag": "LAB_NEO4J", "key": "basic", "label": "Cypher básico", "desc": "MATCH, count, ORDER BY — stats del grafo, influencers, comunidades", "exercises": 3},
            {"flag": "LAB_NEO4J", "key": "intermediate", "label": "Cypher intermedio", "desc": "Patrones en V, intereses comunes, usuarios puente, solapamiento social", "exercises": 5},
            {"flag": "LAB_NEO4J", "key": "advanced", "label": "Cypher avanzado", "desc": "shortestPath, red ego, alcance por saltos, distancia a influencers", "exercises": 4},
            {"flag": "LAB_ML", "key": "supervised", "label": "ML supervisado", "desc": "Spam, engagement, viralidad, churn (RandomForest, GBT, regresión)", "exercises": 4},
            {"flag": "LAB_ML", "key": "unsupervised", "label": "ML no supervisado", "desc": "Clustering de usuarios (KMeans + silhouette)", "exercises": 1},
            {"flag": "LAB_ML", "key": "graph_ml", "label": "Graph ML", "desc": "Recomendador de follows (hashtags compartidos + friends-of-friends)", "exercises": 1},
        ],
    },
    "preprolab": {
        "name": "PreproLab",
        "tagline": "Preprocesamiento (Tema 5)",
        "description": "Las 8 técnicas del Tema 5 sobre una flota de robots con mantenimiento predictivo, más un Pipeline Studio que compara modelos según el preprocesamiento elegido.",
        "url_internal": "http://app-preprolab:8002",
        "url_public": "http://localhost:8002",
        "container": "quasar-preprolab",
        "status_path": "/api/preprolab/lab/status",
        "docs": "http://localhost:8002/docs",
        "readme": "https://github.com/PabloCCanizares/Quasar/blob/main/apps/preprolab/README.md",
        "color": "#1d9bf0",
        "tech": ["Spark", "pandas", "scikit-learn", "Plotly", "FastAPI"],
        "architecture": [
            {"label": "Seed", "sub": "flota robots: 4 tablas"},
            {"label": "Spark ETL", "sub": "raw JSONL → silver parquet"},
            {"label": "8 bloques Tema 5", "sub": "missing · outliers · transform · normalize · reduce…"},
            {"label": "Pipeline Studio", "sub": "compone bloques → RandomForest"},
            {"label": "Web (Plotly)", "sub": "comparativa AUC · F1 · ROC"},
        ],
        "tasks": {
            "seed": "Generar flota de robots",
            "etl": "ETL Spark → silver",
        },
        "uses_neo4j": False,
        "uses_mongo": True,
        "blocks": [
            {"flag": "LAB_PREPROLAB", "key": "eda", "label": "EDA", "desc": "Análisis univariable, missing matrix, correlaciones", "exercises": 3},
            {"flag": "LAB_PREPROLAB", "key": "missing", "label": "Valores perdidos", "desc": "Drop, media/mediana/moda, KNN, K-Means, comparativa MCAR/MAR/MNAR", "exercises": 5},
            {"flag": "LAB_PREPROLAB", "key": "outliers", "label": "Outliers + ruido", "desc": "IQR, Z-score, gestión + noise filters EF/CVCF/IPF", "exercises": 4},
            {"flag": "LAB_PREPROLAB", "key": "integration", "label": "Integración", "desc": "union, 4 joins, Pearson + Cramér's V, dedup por correlación", "exercises": 4},
            {"flag": "LAB_PREPROLAB", "key": "transform", "label": "Transformación", "desc": "One-hot, ordinal, multi-flag, discretización (eq-width/freq/MDLP), groupby", "exercises": 5},
            {"flag": "LAB_PREPROLAB", "key": "normalize", "label": "Normalización", "desc": "Z-score, Min-Max, Robust, Decimal + comparador de sensibilidad a outliers", "exercises": 5},
            {"flag": "LAB_PREPROLAB", "key": "reduce_dim", "label": "Reducción dimensional", "desc": "PCA, t-SNE, feature selection (filter/wrapper/embedded)", "exercises": 6},
            {"flag": "LAB_PREPROLAB", "key": "reduce_inst", "label": "Reducción de instancias", "desc": "SRSWOR, estratificado, balanceado, por clusters, K-Means compresión", "exercises": 5},
        ],
    },
    "llmprep": {
        "name": "LLM Lab",
        "tagline": "Corpus para LLMs",
        "description": "Preparación de corpus para modelos de lenguaje: limpieza, deduplicación (MinHash + grafo Neo4j), tokenización BPE y entrenamiento con la demo culminante corpus sucio vs limpio.",
        "url_internal": "http://app-llmprep:8001",
        "url_public": "http://localhost:8001",
        "container": "quasar-llmprep",
        "status_path": "/api/llmprep/lab/status",
        "docs": "http://localhost:8001/docs",
        "readme": "https://github.com/PabloCCanizares/Quasar/blob/main/apps/llmprep/README.md",
        "color": "#a78bfa",
        "tech": ["Spark", "MinHash/LSH", "Neo4j", "BPE", "n-gram LM", "FastAPI"],
        "architecture": [
            {"label": "Corpus sucio", "sub": "tipo Wikipedia ES"},
            {"label": "Spark ETL", "sub": "raw → silver + perfil de ruido"},
            {"label": "Clean", "sub": "encoding · HTML · idioma · PII"},
            {"label": "Dedup", "sub": "MinHash → Neo4j SIMILAR_TO"},
            {"label": "Tokenize", "sub": "BPE → shards .bin"},
            {"label": "Train", "sub": "demo sucio vs limpio (perplexity)"},
        ],
        "tasks": {
            "ingest": "Generar corpus sucio",
            "etl": "ETL Spark → silver",
        },
        "uses_neo4j": True,
        "uses_mongo": True,
        "blocks": [
            {"flag": "LAB_LLMPREP", "key": "clean", "label": "Clean", "desc": "fix encoding, strip HTML, filtro longitud/idioma, PII removal", "exercises": 6},
            {"flag": "LAB_LLMPREP", "key": "dedup", "label": "Dedup", "desc": "exact, MinHash, LSH + grafo SIMILAR_TO en Neo4j + Cypher", "exercises": 5},
            {"flag": "LAB_LLMPREP", "key": "tokenize", "label": "Tokenize", "desc": "BPE desde cero + shards .bin estilo nanoGPT", "exercises": 4},
            {"flag": "LAB_LLMPREP", "key": "train", "label": "Train ★", "desc": "Modelo de lenguaje + demo sucio vs limpio (perplexity)", "exercises": 3},
        ],
    },
    "streamlab": {
        "name": "StreamLab",
        "tagline": "Datos en tiempo real",
        "description": "La misma flota de robots, pero emitiendo en vivo. Ventanas temporales, watermarks y estado incremental con Spark Structured Streaming, para responder cuando los datos todavía están llegando.",
        "url_internal": "http://app-streamlab:8003",
        "url_public": "http://localhost:8003",
        "container": "quasar-streamlab",
        "status_path": "/api/streamlab/lab/status",
        "docs": "http://localhost:8003/docs",
        "readme": "https://github.com/PabloCCanizares/Quasar/blob/main/apps/streamlab/README.md",
        "color": "#f59e0b",
        "tech": ["Structured Streaming", "Spark", "MongoDB", "FastAPI"],
        "architecture": [
            {"label": "Emisor", "sub": "telemetría en vivo → micro-lotes"},
            {"label": "Buzón raw", "sub": "carpeta que Spark vigila"},
            {"label": "Structured Streaming", "sub": "ventanas · watermark · estado"},
            {"split": [
                {"label": "MongoDB", "sub": "agregados del centro de control"},
                {"label": "Checkpoints", "sub": "por dónde iba la consulta"},
            ]},
            {"label": "Web", "sub": "batch vs streaming en vivo"},
        ],
        "tasks": {"emit": "Emitir telemetría de la flota"},
        "uses_neo4j": False,
        "uses_mongo": True,
        "blocks": [
            {"flag": "LAB_STREAMLAB", "key": "windows", "label": "Ventanas", "desc": "Tumbling, sliding y de sesión sobre la telemetría de la flota", "exercises": 6},
            {"flag": "LAB_STREAMLAB", "key": "late", "label": "Datos tardíos", "desc": "Watermark: qué se corrige con lo que llega tarde y qué se descarta", "exercises": 6},
            {"flag": "LAB_STREAMLAB", "key": "state", "label": "Estado ★", "desc": "Agregación incremental, checkpoints y dedup por reintento", "exercises": 6},
        ],
    },
}


# ============================================================
# Temario de la asignatura
# ============================================================
# La portada del Hub es el índice del curso. Cada tema apunta a la app donde
# se practica (`app`) o no apunta a ninguna (`app: None`), y entonces es
# material de teoría: se ve, pero avisa de que todavía no hay laboratorio.
#
# El nº de ejercicios NO se escribe aquí: se saca del catálogo de arriba, que
# es quien lo sabe. Así no hay dos sitios que puedan contradecirse.

UNIDADES = [
    {
        "clave": "sistemas",
        "titulo": "Sistemas de datos masivos",
        "pregunta": "¿Qué cambia cuando los datos no caben?",
        "oficial": True,
        "temas": [
            {
                "titulo": "Qué hace masivo a un dato",
                "resumen": "No es el tamaño: es que deja de caber en una máquina y hay que repartirlo. Ahí aparecen problemas que antes no existían.",
                "app": None,
                "minutos": 45,
                "objetivo": "reconocer cuándo un problema deja de ser de una máquina y qué implica repartirlo",
                "preguntas": [
                    {
                        "enunciado": "¿Qué distingue de verdad a un sistema de datos masivos?",
                        "opciones": ["Que los datos ocupen varios terabytes", "Que ya no quepan en una máquina y haya que repartirlos", "Que se usen herramientas como Spark o Hadoop"],
                        "correcta": 1,
                        "porque": "No es el tamaño absoluto: es el momento en que una máquina deja de bastar. Ahí aparecen el particionado, la coordinación y los fallos parciales, que son los problemas de verdad. La herramienta es consecuencia, no causa.",
                    },
                    {
                        "enunciado": "Ante un corte de red, el teorema CAP dice que un sistema distribuido…",
                        "opciones": ["puede mantener coherencia y disponibilidad si está bien diseñado", "tiene que elegir entre seguir respondiendo o seguir siendo coherente", "deja de funcionar hasta que se restablezca la red"],
                        "correcta": 1,
                        "porque": "La partición no se elige: ocurre. Lo que sí eliges es qué sacrificas mientras dura. Cada base de datos del curso ya ha tomado esa decisión por ti, y conviene saber cuál.",
                    },
                    {
                        "enunciado": "¿Por qué importa que una operación sea idempotente?",
                        "opciones": ["Porque acelera el procesamiento", "Porque un mensaje puede reenviarse y procesarse dos veces", "Porque reduce el espacio en disco"],
                        "correcta": 1,
                        "porque": "En un sistema distribuido no puedes garantizar que algo se entregue exactamente una vez. Sí puedes hacer que procesarlo dos veces dé el mismo resultado, y eso resuelve el problema por otra vía.",
                    },
                ],
                "material": "Tema 1 · TGDIntro.pdf",
                "teoria": [
                    "Un dato no es masivo por pesar mucho, sino porque ya no cabe en una máquina y hay que repartirlo entre varias. Ese reparto es lo que cambia las reglas: aparecen problemas que en un portátil no existen.",
                    "**Batch frente a streaming.** O procesas un lote completo y respondes cuando termina, o respondes mientras los datos siguen llegando. La primera opción acierta más; la segunda llega antes. Ninguna es mejor: depende de cuándo necesites la respuesta.",
                    "**Escalado horizontal y particionado.** En vez de una máquina más grande, muchas máquinas iguales. Para eso hay que trocear los datos, y cómo los trocees decide qué consultas irán rápidas y cuáles harán hablar a todas las máquinas entre sí.",
                    "**El teorema CAP.** Ante un corte de red, un sistema distribuido elige entre seguir respondiendo o seguir siendo coherente. No puede tener las dos. Cada base de datos que veas en el curso ha tomado ya esa decisión por ti.",
                    "**Idempotencia y backpressure.** Si un mensaje se reenvía, procesarlo dos veces no puede cambiar el resultado. Y si la fuente produce más rápido de lo que consumes, algo tiene que frenar o algo se romperá.",
                ],
            },
        ],
    },
    {
        "clave": "adquisicion",
        "titulo": "Adquisición y almacenamiento",
        "pregunta": "¿De dónde salen y dónde los pongo?",
        "oficial": True,
        "temas": [
            {
                "titulo": "Fuentes de datos y formatos",
                "resumen": "Bases de datos, la web y ficheros. Y por qué CSV, JSON, XML y parquet no son intercambiables.",
                "app": None,
                "minutos": 45,
                "objetivo": "elegir el formato adecuado y anticipar qué problemas trae cada fuente",
                "preguntas": [
                    {
                        "enunciado": "Guardas códigos postales que empiezan por cero. ¿Qué formato te los estropea?",
                        "opciones": ["CSV", "Parquet", "JSON"],
                        "correcta": 0,
                        "porque": "CSV no lleva tipos: quien lo lea decidirá que «08001» es un número y se comerá el cero. Parquet y JSON conservan que era texto.",
                    },
                    {
                        "enunciado": "¿Por qué parquet es el formato del data lake y no CSV?",
                        "opciones": ["Porque siempre ocupa menos", "Porque guarda por columnas: si necesitas dos de cincuenta, lee solo esas dos", "Porque se puede abrir con un editor de texto"],
                        "correcta": 1,
                        "porque": "El almacenamiento columnar es lo que permite leer solo lo que hace falta. En una tabla ancha, eso es la diferencia entre segundos y minutos.",
                    },
                    {
                        "enunciado": "En la capa raw del data lake, ¿qué guardas?",
                        "opciones": ["Los datos ya limpios y tipados", "Lo que te dieron, tal cual llegó", "Solo las columnas que vas a usar"],
                        "correcta": 1,
                        "porque": "raw es tu copia fiel del origen, con su suciedad incluida. Si limpias ahí, pierdes la posibilidad de volver atrás cuando algo salga raro tres capas más abajo.",
                    },
                ],
                "material": "Tema 2 · adquisición.pdf",
                "teoria": [
                    "Los datos llegan de tres sitios: bases de datos que ya existen, la web, y ficheros que alguien exportó. Cada origen trae sus vicios, y conviene saberlos antes de empezar.",
                    "**CSV** es cómodo y miente mucho: no lleva tipos, así que un código postal con ceros delante se convierte en número y los pierde. Tampoco sabe de jerarquías.",
                    "**JSON** admite estructuras anidadas y es el formato de las APIs, pero repite las claves en cada registro: para volúmenes grandes es un desperdicio de espacio.",
                    "**XML** es más verboso todavía, y aun así sigue siendo el formato de muchos volcados institucionales y semánticos, así que toca saber leerlo.",
                    "**Parquet** guarda por columnas en vez de por filas. Si solo necesitas dos columnas de cincuenta, lee solo esas dos: por eso es el formato del data lake y no CSV.",
                    "La regla práctica: en la capa cruda guardas lo que te dieron, tal cual llegó. En cuanto lo procesas, lo pasas a columnar.",
                ],
            },
            {
                "titulo": "Captura: web scraping e interfaces",
                "resumen": "Cuando no hay API hay que arrancar los datos de la página. BeautifulSoup para HTML estático, Selenium cuando hay JavaScript por medio.",
                "app": None,
                "minutos": 240,
                "objetivo": "extraer datos de una web y saber cuándo hacerlo y cuándo no",
                "preguntas": [
                    {
                        "enunciado": "Una web pinta sus datos con JavaScript después de cargar. ¿Qué usas?",
                        "opciones": ["BeautifulSoup", "Selenium", "Cualquiera de los dos"],
                        "correcta": 1,
                        "porque": "BeautifulSoup parsea el HTML que llega; si los datos los pinta el navegador después, ahí no hay nada que parsear. Selenium ejecuta la página de verdad, a cambio de ser más lento y más frágil.",
                    },
                    {
                        "enunciado": "¿Qué es robots.txt?",
                        "opciones": ["Una barrera técnica que impide el scraping", "Un fichero donde el sitio declara qué te deja recorrer", "Un formato para guardar lo scrapeado"],
                        "correcta": 1,
                        "porque": "No impide nada técnicamente: es una declaración de intenciones que se respeta. Saltárselo no da un error, da un problema de otro tipo.",
                    },
                    {
                        "enunciado": "Hay API disponible y también podrías scrapear la web. ¿Qué eliges?",
                        "opciones": ["Scraping, porque suele dar más datos", "La API: es estable, está documentada y no se rompe con un rediseño", "Los dos, para contrastar"],
                        "correcta": 1,
                        "porque": "Un scraper depende de la estructura de una página que no controlas, así que es código que se rompe solo. Si hay API, el scraping es trabajo extra que además caduca.",
                    },
                ],
                "material": "Tema 2 · adquisición.pdf + notebooks (BeautifulSoup, Spotify API)",
                "teoria": [
                    "Si hay API, se usa la API: es estable, viene documentada y no se rompe porque alguien cambie el diseño. El scraping es el recurso para cuando no la hay.",
                    "**BeautifulSoup** basta cuando el HTML ya trae los datos. Descargas la página, la parseas y buscas por etiqueta o clase.",
                    "**Selenium** hace falta cuando el contenido lo pinta JavaScript después de cargar: entonces no hay nada que parsear hasta que un navegador de verdad ejecute la página. Es más lento y más frágil, así que se usa solo si el primero no llega.",
                    "**Lo que no es técnico también cuenta.** `robots.txt` dice qué te dejan recorrer. Ir demasiado rápido tumba servidores ajenos y te gana un bloqueo. Y que un dato sea accesible no significa que puedas quedártelo ni republicarlo.",
                    "Un scraper es código que se rompe solo: depende de la estructura de una página que no controlas. Escríbelo esperando que falle y comprobando que lo extraído tiene sentido.",
                ],
                "practica": "Práctica 1 — Web scraping",
            },
            {
                "titulo": "Almacenamiento NoSQL",
                "resumen": "Documental y grafo conviviendo. Ninguna base es buena en todo: hay preguntas que solo una de las dos responde bien.",
                "app": "sociallab",
                "bloques": ["basic", "intermediate", "advanced"],
                "minutos": 240,
                "objetivo": "elegir entre documental y grafo según la pregunta, y escribir Cypher sobre un grafo social",
                "preguntas": [
                    {
                        "enunciado": "¿Qué pregunta responde mucho mejor un grafo que una base documental?",
                        "opciones": ["Dame el perfil completo del usuario X", "¿A quién sigue la gente que sigue a X?", "¿Cuántos usuarios hay en total?"],
                        "correcta": 1,
                        "porque": "Eso es un recorrido de dos saltos. En documental sale una cadena de JOINs que empeora con cada salto; en grafo es la operación nativa.",
                    },
                    {
                        "enunciado": "«Persistencia poliglota» significa…",
                        "opciones": ["usar la misma base con varios lenguajes de consulta", "combinar varias bases, cada una para lo que hace bien", "guardar los datos traducidos a varios idiomas"],
                        "correcta": 1,
                        "porque": "Y no sale gratis: mantener dos bases sincronizadas es trabajo. Se acepta ese coste porque cada una responde bien a preguntas que la otra hace fatal.",
                    },
                    {
                        "enunciado": "¿Qué te da MongoDB frente a un esquema rígido?",
                        "opciones": ["Más velocidad en cualquier consulta", "Que dos documentos puedan tener campos distintos sin migrar nada", "Mejores garantías de integridad referencial"],
                        "correcta": 1,
                        "porque": "El esquema flexible es la ventaja y también el riesgo: nada te avisa de que llevas tres meses escribiendo un campo mal escrito.",
                    },
                ],
                "teoria": [
                    "Ninguna base de datos es buena en todo. Por eso aquí conviven dos, y elegir cuál usa cada consulta es parte del trabajo.",
                    "**MongoDB** guarda documentos: cada usuario es un JSON y dos usuarios pueden tener campos distintos sin migrar nada. Va muy bien cuando el esquema cambia con el producto y cuando lo que pides es «dame este documento entero».",
                    "**Neo4j** guarda lo mismo como nodos y aristas. Ahí las preguntas cambian de naturaleza: «¿a quién sigue la gente que sigue a X?» es un recorrido de grafo, no una tabla con JOINs encadenados.",
                    "La prueba está en pedirle a cada una lo que se le da mal. Pídele a Mongo el camino más corto entre dos usuarios, o sus comunidades, y sufrirás; Neo4j lo resuelve en una línea de Cypher. Al revés, guardar un documento con veinte campos anidados en un grafo es forzar la herramienta.",
                    "A esto se le llama **persistencia poliglota**: no elegir una base para todo, sino cada una para lo que hace bien, asumiendo el coste de mantener las dos sincronizadas.",
                ],
            },
            {
                "titulo": "Computación distribuida con Spark",
                "resumen": "El pipeline que lleva de raw a gold. Mismo código en tu portátil que en un cluster: cambia la escala, no la lógica.",
                "app": "sociallab",
                "minutos": 180,
                "objetivo": "escribir un pipeline que corra igual en tu portátil y en un cluster",
                "preguntas": [
                    {
                        "enunciado": "¿Por qué la capa raw no se toca nunca más?",
                        "opciones": ["Para ahorrar espacio en disco", "Para poder volver al origen y rehacer el pipeline si algo sale mal", "Porque Spark no puede escribir en ella"],
                        "correcta": 1,
                        "porque": "Es tu red de seguridad. Si limpiaste sobre los datos originales y descubres un error de criterio semanas después, ya no hay marcha atrás.",
                    },
                    {
                        "enunciado": "El mismo código PySpark corre en tu portátil y en un cluster. ¿Qué cambia?",
                        "opciones": ["Hay que reescribir la lógica para el cluster", "Solo la escala", "Hay que cambiar de lenguaje"],
                        "correcta": 1,
                        "porque": "Esa es la propiedad que hace útil a Spark para aprender: desarrollas con datos pequeños y el mismo script vale cuando crecen.",
                    },
                    {
                        "enunciado": "¿Qué implica que «la lógica viva en el ETL versionado»?",
                        "opciones": ["Que el ETL se guarda dentro de la base de datos", "Que cualquiera puede clonar el repo, ejecutarlo y obtener lo mismo", "Que solo su autor puede ejecutarlo"],
                        "correcta": 1,
                        "porque": "Si un dato depende de que alguien recuerde qué tocó a mano un martes, no lo controlas. Reproducible significa que el proceso, no la persona, explica el resultado.",
                    },
                ],
                "teoria": [
                    "El pipeline que lleva los datos de crudos a servibles. Lo escribes en PySpark y corre igual en tu portátil que en un cluster: cambia la escala, no la lógica.",
                    "**El data lake tiene tres capas.** `raw` es lo que llegó tal cual, con su suciedad incluida, y no se toca nunca más. `silver` ya está limpio y con tipos estables. `gold` está agregado y listo para consumir. raw es materia prima, gold es lo servible.",
                    "Que raw sea intocable es lo que te salva: si algo sale raro tres capas más abajo, siempre puedes volver al origen y rehacer el pipeline entero. Si hubieras limpiado sobre los datos originales, no habría vuelta atrás.",
                    "**Si el ETL está mal, la app enseña basura**, por bonita que sea la interfaz. Todo lo que se ve aguas abajo depende de este paso, y por eso es donde más conviene mirar cuando algo no cuadra.",
                    "**La lógica vive en el ETL, versionado en git**, no en pasos manuales que nadie recuerda. Eso es lo que hace que otro pueda clonar el repo, ejecutar el pipeline y obtener exactamente lo mismo. Si no puedes reconstruir un dato desde su origen, no lo controlas: lo estás improvisando.",
                ],
                "enlace": {"texto": "Lanzar el ETL", "vista": "status"},
            },
        ],
    },
    {
        "clave": "eda",
        "titulo": "Análisis exploratorio",
        "pregunta": "¿Qué me dicen los datos antes de tocarlos?",
        "oficial": True,
        "temas": [
            {
                "titulo": "EDA en datos masivos",
                "resumen": "Mirar antes de arreglar: distribuciones, valores que faltan y correlaciones. Análisis descriptivo sobre datos que no caben en pantalla.",
                "app": "preprolab",
                "bloques": ["eda"],
                "minutos": 90,
                "objetivo": "hacerte una idea de un dataset que no puedes mirar entero",
                "preguntas": [
                    {
                        "enunciado": "La media y la mediana de una columna se separan mucho. ¿Qué indica?",
                        "opciones": ["Que hay un error de cálculo", "Que la distribución está sesgada o hay valores extremos", "Que faltan datos en esa columna"],
                        "correcta": 1,
                        "porque": "La mediana aguanta los extremos y la media no. Que se separen es justo la señal que buscas para saber dónde mirar después.",
                    },
                    {
                        "enunciado": "¿Por qué importa que dos columnas se queden vacías siempre a la vez?",
                        "opciones": ["Porque ocupa más espacio", "Porque señala una causa común, y eso decide qué imputación tiene sentido", "Porque hay que borrar las dos"],
                        "correcta": 1,
                        "porque": "Los nulos que van juntos no son casualidad: apuntan a un mecanismo. Y saber el mecanismo es lo que separa imputar con criterio de rellenar huecos.",
                    },
                    {
                        "enunciado": "Dos columnas con correlación de 0,99. ¿Qué sugiere?",
                        "opciones": ["Que las dos son muy importantes", "Que una de las dos probablemente sobra", "Que hay un error en los datos"],
                        "correcta": 1,
                        "porque": "Si una explica a la otra casi por completo, conservar ambas añade poco y desestabiliza los modelos. Es una decisión de reducción que verás más adelante.",
                    },
                ],
                "teoria": [
                    "Antes de arreglar nada hay que mirar. El análisis exploratorio es esa mirada: qué hay, cómo se reparte y qué falta, sobre un dataset que no puedes abrir entero en pantalla.",
                    "**Análisis univariable.** Para cada columna: media, mediana, desviación, mínimo, máximo y cuartiles. La media y la mediana separándose ya es una señal — significa que la distribución está sesgada o que hay valores extremos tirando de la media.",
                    "**Matriz de valores perdidos.** No basta con cuántos nulos hay: importa si aparecen juntos. Que dos columnas se queden vacías siempre a la vez señala una causa común, y esa causa decide qué imputación tiene sentido.",
                    "**Correlaciones.** Pares de columnas que se mueven juntas. Una correlación muy alta suele significar que una de las dos sobra, y eso ya es una decisión de reducción que tomarás más adelante.",
                    "El objetivo no es producir gráficos bonitos: es llegar al preprocesamiento sabiendo qué te vas a encontrar en vez de descubrirlo a golpes.",
                ],
            },
        ],
    },
    {
        "clave": "preprocesamiento",
        "titulo": "Preprocesamiento y limpieza",
        "pregunta": "¿Cómo los dejo utilizables?",
        "oficial": True,
        "temas": [
            {
                "titulo": "Limpieza de datos",
                "resumen": "Valores perdidos (MCAR, MAR, MNAR), outliers y ruido en las etiquetas. Qué imputar, qué eliminar y qué dejar como está.",
                "app": "preprolab",
                "bloques": ["missing", "outliers"],
                "minutos": 240,
                "objetivo": "tratar nulos y outliers con criterio, y medir si el arreglo mejoró algo",
                "preguntas": [
                    {
                        "enunciado": "Los robots con firmware viejo no reportan cierto sensor. ¿Qué mecanismo es?",
                        "opciones": ["MCAR", "MAR", "MNAR"],
                        "correcta": 1,
                        "porque": "Falta según otra columna que SÍ ves (la versión de firmware). Eso es MAR, y es buena noticia: al ser observable, puedes aprovecharla para imputar mejor.",
                    },
                    {
                        "enunciado": "¿Por qué KNN conserva más variabilidad que imputar por la media?",
                        "opciones": ["Porque usa más memoria", "Porque aprovecha la relación con otras columnas en vez de un único valor", "Porque imputa valores más altos"],
                        "correcta": 1,
                        "porque": "La media mete el mismo número en todos los huecos y aplasta la varianza. KNN busca instancias parecidas, así que reparte valores distintos.",
                    },
                    {
                        "enunciado": "Un sensor descalibrado marca 1000 °C; un robot de pruebas marca 85 °C. ¿Qué haces?",
                        "opciones": ["Quitar los dos: son outliers", "Quitar el de 1000 y conservar el de 85", "Conservar los dos"],
                        "correcta": 1,
                        "porque": "El primero es un error de medición y el segundo es un extremo válido. Confundirlos borra justo la información interesante.",
                    },
                ],
                "teoria": [
                    "Los datos reales no vienen limpios: faltan campos, hay valores imposibles y las etiquetas tienen errores. **Nadie va a tener datos limpios en su carrera**; aprender a arreglarlos es de lo que va esto.",
                    "**Los valores perdidos no son todos iguales.** MCAR es que falten al azar. MAR es que falten según otra columna que sí ves — por ejemplo, los robots con firmware viejo no reportan cierto sensor. MNAR es que falten según el propio valor oculto, que es el caso peor porque no puedes detectarlo desde los datos.",
                    "Saber cuál tienes decide qué hacer. Imputar por la media es rápido y siempre reduce la varianza. KNN y K-Means miran otras columnas y conservan más variabilidad, precisamente porque aprovechan la relación que causaba el MAR.",
                    "**Los outliers tampoco son todos iguales.** Uno de medición (un sensor descalibrado marcando 1000 °C) hay que quitarlo. Uno extremo pero válido (un robot de pruebas al máximo) es información. Confundirlos borra justo lo interesante.",
                    "**Y hay ruido en las etiquetas**, no solo en los valores. Filtros como EF, CVCF e IPF detectan instancias mal clasificadas; al pasar de conservador a agresivo suben el recall y bajan la precisión, y ese intercambio lo eliges tú.",
                ],
            },
            {
                "titulo": "Integración de datos",
                "resumen": "Juntar tablas de distinta procedencia sin duplicar ni perder: uniones, joins y detección de columnas redundantes.",
                "app": "preprolab",
                "bloques": ["integration"],
                "minutos": 120,
                "objetivo": "combinar fuentes distintas detectando lo que sobra y lo que no cuadra",
                "preguntas": [
                    {
                        "enunciado": "Un inner join te devuelve más filas que cualquiera de las dos tablas. ¿Qué pasa?",
                        "opciones": ["Es un error del join", "Hay claves repetidas en algún lado y se multiplican las combinaciones", "Has usado outer sin darte cuenta"],
                        "correcta": 1,
                        "porque": "Con claves duplicadas, cada coincidencia se cruza con todas las del otro lado. No es un fallo del join: es un aviso de que la clave no identifica lo que creías.",
                    },
                    {
                        "enunciado": "¿Para qué sirve Cramér's V?",
                        "opciones": ["Medir correlación entre variables numéricas", "Medir asociación entre variables categóricas", "Detectar valores perdidos"],
                        "correcta": 1,
                        "porque": "Pearson necesita números. Para categóricas se parte del chi² de la tabla de contingencia y se normaliza, que es lo que hace Cramér's V.",
                    },
                    {
                        "enunciado": "¿Por qué molesta tener dos columnas casi idénticas en un modelo?",
                        "opciones": ["Porque ocupan espacio", "Porque el peso se reparte de forma arbitraria entre ellas", "Porque ralentizan la lectura"],
                        "correcta": 1,
                        "porque": "El modelo no sabe a cuál atribuir el efecto, así que la importancia que reporta deja de ser fiable y pequeños cambios en los datos la mueven mucho.",
                    },
                ],
                "teoria": [
                    "Casi nunca hay una sola fuente. Integrar es juntar varias sin duplicar lo que ya estaba ni perder lo que solo estaba en una.",
                    "**Unir por filas o por columnas.** Concatenar dos tablas con el mismo esquema añade filas. Un join las cruza por una clave y añade columnas. Confundirlos produce tablas que parecen correctas y no lo son.",
                    "**Los cuatro joins importan.** El inner se queda con lo que está en ambas; left y right conservan un lado entero; outer no pierde nada y llena de nulos. Y ojo con las claves repetidas: un inner puede salir con más filas que cualquiera de las dos tablas de partida.",
                    "**Detectar redundancia.** Si dos columnas dicen lo mismo, una sobra. Para numéricas se mide con Pearson; para categóricas, con Cramér's V, que generaliza la idea a tablas de contingencia.",
                    "Quitar una columna redundante no es solo ahorrar espacio: dos variables casi idénticas desestabilizan muchos modelos, porque el peso se reparte de forma arbitraria entre ellas.",
                ],
            },
            {
                "titulo": "Transformación de datos",
                "resumen": "Dejar los datos en la forma que el modelo entiende: codificación, discretización y las cuatro normalizaciones.",
                "app": "preprolab",
                "bloques": ["transform", "normalize"],
                "minutos": 240,
                "objetivo": "codificar y escalar sabiendo qué le hace cada técnica a la distribución",
                "preguntas": [
                    {
                        "enunciado": "Tienes severidad: INFO, WARN, ERROR, CRITICAL. ¿Qué codificación usas?",
                        "opciones": ["One-hot", "Ordinal, respetando ese orden", "Cualquiera de las dos"],
                        "correcta": 1,
                        "porque": "Aquí el orden existe de verdad y contiene información. One-hot la tiraría. Al revés también pasa: poner ordinal donde no hay orden le cuenta una mentira al modelo.",
                    },
                    {
                        "enunciado": "Tu columna tiene outliers y aplicas Min-Max. ¿Qué ocurre?",
                        "opciones": ["Los outliers desaparecen", "Casi todos los datos se apelotonan en una franja diminuta", "La distribución se vuelve normal"],
                        "correcta": 1,
                        "porque": "Min-Max usa el mínimo y el máximo, y un solo valor extremo estira el rango entero. Robust usa mediana e IQR y por eso aguanta.",
                    },
                    {
                        "enunciado": "¿Qué diferencia a MDLP de la discretización equal-width?",
                        "opciones": ["MDLP hace tramos del mismo tamaño", "MDLP mira la variable objetivo y corta donde cambia la clase", "MDLP es simplemente más rápido"],
                        "correcta": 1,
                        "porque": "Es discretización supervisada: los cortes no son arbitrarios, caen donde de verdad cambia el comportamiento de lo que quieres predecir.",
                    },
                ],
                "teoria": [
                    "Dejar los datos en la forma que el modelo entiende. Un algoritmo no sabe qué es «Manufactura Centauri» ni le da igual que una columna vaya de 0 a 1 y otra de 0 a 100.000.",
                    "**Codificar categorías.** One-hot crea una columna binaria por valor y no impone orden. El encoding ordinal sí lo impone, y solo vale si el orden existe de verdad (INFO < WARN < ERROR < CRITICAL). Usarlo donde no hay orden le está diciendo al modelo una mentira.",
                    "**Discretizar.** Convertir una variable continua en tramos. Equal-width parte el rango en trozos iguales; equal-frequency parte en trozos con la misma cantidad de datos; MDLP mira además la variable objetivo y corta donde cambia la proporción de la clase.",
                    "**Normalizar.** Z-score deja media 0 y desviación 1. Min-Max mete todo en [0,1]. Robust usa mediana e IQR. Decimal solo mueve la coma.",
                    "La elección importa más de lo que parece: **con outliers, Min-Max apelotona casi todos los datos en una franja diminuta** mientras Robust los mantiene repartidos. Es el mismo dato y dos representaciones que llevan a modelos distintos.",
                ],
            },
            {
                "titulo": "Reducción de datos",
                "resumen": "Menos columnas y menos filas sin perder lo que importa: PCA, selección de características y muestreo.",
                "app": "preprolab",
                "bloques": ["reduce_dim", "reduce_inst"],
                "minutos": 240,
                "objetivo": "quedarte con menos datos sin quedarte sin información",
                "preguntas": [
                    {
                        "enunciado": "¿Qué pierdes al aplicar PCA?",
                        "opciones": ["Buena parte de la varianza", "La interpretabilidad: las componentes ya no significan nada concreto", "Filas del dataset"],
                        "correcta": 1,
                        "porque": "La varianza se conserva casi entera si eliges bien el número de componentes. Lo que se va es poder decir «esta variable es la temperatura».",
                    },
                    {
                        "enunciado": "Filter, wrapper y embedded eligen las mismas variables. ¿Qué significa?",
                        "opciones": ["Que hay un error en el cálculo", "Que la selección es fiable", "Que sobran todas menos una"],
                        "correcta": 1,
                        "porque": "Tres criterios distintos coincidiendo es una señal fuerte. Cuando discrepan, es que ninguna variable manda con claridad y conviene desconfiar de la selección.",
                    },
                    {
                        "enunciado": "Quieres menos filas conservando la proporción de una clase minoritaria. ¿Qué usas?",
                        "opciones": ["Muestreo aleatorio simple", "Muestreo estratificado", "Cuantización con K-Means"],
                        "correcta": 1,
                        "porque": "El aleatorio simple puede dejarte casi sin la clase pequeña justo por ser pequeña. El estratificado muestrea dentro de cada clase y mantiene las proporciones.",
                    },
                ],
                "teoria": [
                    "Menos datos que procesar, sin quedarte sin información. Se puede reducir por dos lados: menos columnas o menos filas.",
                    "**Menos columnas por proyección.** PCA construye combinaciones nuevas que concentran la varianza; con columnas muy correlacionadas, unas pocas componentes explican casi todo. El precio es que las componentes ya no significan nada interpretable.",
                    "**Menos columnas por selección.** Aquí sí se conservan las originales. Los métodos filter puntúan cada variable por su cuenta y son rápidos; los wrapper entrenan un modelo por combinación y son lentos pero certeros; los embedded lo deciden durante el propio entrenamiento, como Lasso o la importancia de un RandomForest.",
                    "Cuando las tres familias coinciden en las mismas variables, puedes fiarte de la selección. Cuando discrepan, es señal de que ninguna manda con claridad.",
                    "**Menos filas.** El muestreo aleatorio simple es el más sencillo pero puede cargarse una clase minoritaria; el estratificado conserva las proporciones; el balanceado las cambia a propósito. Y la cuantización con K-Means sustituye grupos enteros por su centroide: comprime muchísimo, pero lo que queda ya no son filas reales.",
                ],
            },
        ],
    },
    {
        "clave": "ampliacion",
        "titulo": "Ampliación",
        "pregunta": "Más allá del programa",
        "oficial": False,
        "temas": [
            {
                "titulo": "Datos para modelos de lenguaje",
                "resumen": "Limpiar un corpus, quitar casi-duplicados con MinHash y tokenizar con BPE. Mismo modelo, corpus sucio y limpio: la perplejidad baja.",
                "app": "llmprep",
                "minutos": 300,
                "objetivo": "preparar un corpus y comprobar que la limpieza cambia lo que el modelo aprende",
                "preguntas": [
                    {
                        "enunciado": "¿Por qué los casi-duplicados hacen más daño que los exactos?",
                        "opciones": ["Porque ocupan más espacio", "Porque no los pilla un hash y el modelo memoriza lo repetido", "Porque son más difíciles de leer"],
                        "correcta": 1,
                        "porque": "Un duplicado exacto lo quita cualquier hash. El casi-duplicado pasa el filtro y sigue sobrerrepresentando el mismo contenido en el entrenamiento.",
                    },
                    {
                        "enunciado": "¿Para qué sirve MinHash?",
                        "opciones": ["Cifrar el corpus", "Estimar el parecido entre documentos sin compararlos todos con todos", "Comprimir el texto"],
                        "correcta": 1,
                        "porque": "Comparar todos los pares es inviable en un corpus grande. MinHash resume cada documento en una firma cuya coincidencia estima el Jaccard real.",
                    },
                    {
                        "enunciado": "Entrenas el mismo modelo con el corpus sucio y con el limpio. ¿Qué esperas?",
                        "opciones": ["La misma perplejidad", "Menor perplejidad con el limpio", "Menor perplejidad con el sucio"],
                        "correcta": 1,
                        "porque": "Es la demostración que cierra el bloque: no cambió el modelo, cambiaron los datos. Y eso resume para qué sirve todo el preprocesamiento.",
                    },
                ],
                "teoria": [
                    "Un modelo de lenguaje se entrena con un corpus, y prepararlo es un pipeline de datos como cualquier otro: limpiar, deduplicar, transformar y medir.",
                    "**Limpiar.** Encoding roto, HTML residual, textos en otro idioma, datos personales. El orden importa: reparar el encoding antes de detectar idioma evita descartar textos que solo estaban mal codificados.",
                    "**Deduplicar.** Los duplicados exactos se pillan con un hash. Los casi-duplicados no, y son los que más daño hacen: el modelo memoriza lo repetido. **MinHash** estima el parecido entre documentos sin compararlos todos con todos, y **LSH** agrupa candidatos para no revisar millones de pares.",
                    "**Tokenizar.** El modelo no ve letras, ve tokens. BPE aprende del propio corpus qué trozos conviene fusionar, y por eso un corpus sucio genera vocabulario basura: restos de HTML y referencias acaban siendo tokens.",
                    "**Y la demostración que cierra todo:** el mismo modelo entrenado con el corpus sucio y con el limpio. La perplejidad baja. No cambió el modelo, cambiaron los datos.",
                ],
            },
            {
                "titulo": "Procesamiento en tiempo real",
                "resumen": "Ventanas, watermarks y estado incremental. Una respuesta correcta que llega tarde es otra forma de estar equivocada.",
                "app": "streamlab",
                "minutos": 300,
                "objetivo": "responder mientras los datos siguen llegando, y decidir cuánto esperar",
                "preguntas": [
                    {
                        "enunciado": "¿Por qué es mala idea agrupar por hora de llegada en vez de por hora del evento?",
                        "opciones": ["Porque es más lento", "Porque el resultado cambia según cómo vaya la red", "Porque Spark no lo permite"],
                        "correcta": 1,
                        "porque": "Si la respuesta depende de si hubo un corte de cobertura, no es una respuesta sobre los datos: es una respuesta sobre la red.",
                    },
                    {
                        "enunciado": "Una lectura llega 3 minutos tarde y tus ventanas son de 5 minutos. ¿Se descarta?",
                        "opciones": ["Sí, siempre que haya watermark", "No necesariamente: su ventana puede seguir abierta", "Solo si el watermark es mayor que 3 minutos"],
                        "correcta": 1,
                        "porque": "El watermark no actúa solo. Una lectura se pierde cuando su ventana ya se cerró, y eso depende también del tamaño de la ventana. Se eligen juntos.",
                    },
                    {
                        "enunciado": "¿Qué pasa si no pones watermark en una agregación por ventana?",
                        "opciones": ["Se descartan todos los datos tardíos", "No se descarta nada, pero el estado no se libera nunca", "Spark falla al arrancar"],
                        "correcta": 1,
                        "porque": "Sin watermark, Spark no sabe cuándo una ventana está terminada, así que las guarda todas por si acaso. En un flujo que no acaba, eso crece sin límite.",
                    },
                ],
                "teoria": [
                    "Todo lo anterior es batch: coges un lote, lo procesas entero y guardas. En streaming los datos siguen llegando mientras respondes, así que no puedes esperar a tenerlo todo ni volver atrás a releerlo.",
                    "**Hay dos tiempos por dato:** cuándo ocurrió y cuándo llegó. Que no coincidan es lo que hace difícil el streaming, y agrupar por el segundo da resultados que cambian según cómo vaya la red.",
                    "**Ventanas.** Como el flujo no termina, se agrupa por tramos de tiempo: fijas, deslizantes (que se solapan y reaccionan antes) o de sesión, que se cierran solas tras un silencio y delatan a quien dejó de emitir.",
                    "**Watermarks.** Si quieres cerrar una ventana y dar una respuesta, tienes que decidir hasta cuándo esperas a los rezagados. Esa decisión no es gratis: lo que llegue después se descarta. Cuanto más esperas, menos pierdes y más tardas.",
                    "**Estado y checkpoints.** Agregar un flujo infinito cabe en memoria finita porque el estado se libera cuando el watermark cierra ventanas. Y el checkpoint es lo que permite que un reinicio retome donde iba en vez de contarlo todo otra vez.",
                    "La idea que lo resume: **una respuesta correcta que llega tarde es otra forma de estar equivocada.**",
                ],
            },
            {
                "titulo": "Machine Learning sobre datos masivos",
                "resumen": "Supervisado, no supervisado y sobre grafo, con una fuga de datos puesta a propósito para aprender a olerla.",
                "app": "sociallab",
                "bloques": ["supervised", "unsupervised", "graph_ml"],
                "minutos": 180,
                "objetivo": "entrenar sobre datos limpios y detectar cuándo un modelo es sospechosamente bueno",
                "preguntas": [
                    {
                        "enunciado": "Un modelo da un AUC de 0,99 en un problema difícil. ¿Qué sospechas primero?",
                        "opciones": ["Que el modelo es excelente", "Que hay fuga de datos: ve información que no tendría en producción", "Que hay pocos datos de test"],
                        "correcta": 1,
                        "porque": "Una métrica demasiado buena casi siempre significa que alguna variable contiene, directa o indirectamente, la respuesta. En producción esa variable no estará.",
                    },
                    {
                        "enunciado": "¿Cómo evalúas un clustering, que no tiene etiquetas?",
                        "opciones": ["Con AUC", "Con métricas internas como el coeficiente de silueta", "No se puede evaluar"],
                        "correcta": 1,
                        "porque": "Sin verdad de referencia se mide la propia estructura: cómo de compactos son los grupos y cómo de separados están entre sí.",
                    },
                    {
                        "enunciado": "Un recomendador «sobre grafo» se basa en…",
                        "opciones": ["el contenido de las publicaciones", "la forma de la red: amigos de amigos, intereses compartidos", "la antigüedad de la cuenta"],
                        "correcta": 1,
                        "porque": "Es donde el grafo deja de ser un almacén y pasa a ser información: la estructura de las relaciones predice por sí sola.",
                    },
                ],
                "teoria": [
                    "Con los datos ya limpios se entrenan los modelos. Aquí se ven las tres familias sobre el mismo dataset, para que la diferencia sea de enfoque y no de dominio.",
                    "**Supervisado.** Aprender de ejemplos etiquetados: detectar spam, predecir engagement o abandono. Se evalúa separando entrenamiento de prueba, con AUC o F1 según lo desequilibradas que estén las clases.",
                    "**No supervisado.** Encontrar estructura sin etiquetas: agrupar usuarios parecidos con K-Means. Como no hay respuesta correcta, se mide con métricas internas como el coeficiente de silueta.",
                    "**Sobre grafo.** Recomendar a quién seguir usando la forma de la red —amigos de amigos, intereses compartidos— y no solo el contenido. Es donde el grafo del tema 4 deja de ser un almacén y pasa a ser información.",
                    "**Y una trampa puesta a propósito:** uno de los modelos tiene una fuga de datos deliberada. Su métrica sale sospechosamente buena porque está viendo información que en producción no tendría. Aprender a olerlo vale más que cualquiera de los seis modelos.",
                ],
            },
        ],
    },
]


def temario() -> list[dict]:
    """El temario con los datos del catálogo ya resueltos.

    Rellena, por cada tema con laboratorio, el color, la URL y cuántos
    ejercicios tiene (contando solo sus bloques si el tema usa una parte
    concreta de la app). Numera los temas de corrido, como un índice.
    """
    salida = []
    n = 0
    for unidad in UNIDADES:
        temas = []
        for tema in unidad["temas"]:
            n += 1
            item = {"n": n, "titulo": tema["titulo"], "resumen": tema["resumen"],
                    "enlace": tema.get("enlace"),
                    "minutos": tema.get("minutos"),
                    "objetivo": tema.get("objetivo"),
                    # Lección corta para los temas sin laboratorio, con la
                    # referencia a los apuntes de clase. No duplica las
                    # transparencias: orienta y remite a ellas.
                    "teoria": tema.get("teoria"),
                    "material": tema.get("material"),
                    "practica": tema.get("practica"),
                    # Cuestionario de ensayo: sin nota y sin enviarse a
                    # ningún sitio. Sirve para llegar preparado a los
                    # cuestionarios evaluables, no para sustituirlos.
                    "preguntas": tema.get("preguntas")}
            meta = APPS.get(tema["app"]) if tema.get("app") else None
            if meta:
                claves = tema.get("bloques")
                bloques = [b for b in meta["blocks"]
                           if claves is None or b["key"] in claves]
                item.update({
                    "app": tema["app"],
                    "app_nombre": meta["name"],
                    "color": meta["color"],
                    "url": meta["url_public"],
                    "ejercicios": sum(b["exercises"] for b in bloques),
                    # Detalle de los bloques, para que la página del tema
                    # pueda listar qué se practica sin volver a preguntar.
                    "bloques": [
                        {"key": b["key"], "label": b["label"],
                         "desc": b["desc"], "exercises": b["exercises"],
                         "flag": b["flag"]}
                        for b in bloques
                    ],
                })
            else:
                item.update({"app": None, "color": None, "ejercicios": 0})
            temas.append(item)
        salida.append({
            "clave": unidad["clave"], "titulo": unidad["titulo"],
            "pregunta": unidad["pregunta"], "temas": temas,
            # `oficial` distingue el programa de la guía docente de lo que es
            # material adicional: el alumno tiene que saber qué le entra.
            "oficial": unidad.get("oficial", True),
            "minutos": sum(x["minutos"] or 0 for x in temas),
        })
    return salida


def app_block_keys(app_key: str, flag: str) -> list[str]:
    """Bloques válidos de un flag concreto (para validación de control)."""
    meta = APPS.get(app_key)
    if not meta:
        return []
    return [b["key"] for b in meta["blocks"] if b["flag"] == flag]


def all_flags() -> dict[str, list[str]]:
    """Mapa flag → lista de block keys, de todas las apps."""
    out: dict[str, list[str]] = {}
    for meta in APPS.values():
        for b in meta["blocks"]:
            out.setdefault(b["flag"], []).append(b["key"])
    return out


def total_exercises() -> int:
    return sum(b["exercises"] for m in APPS.values() for b in m["blocks"])
