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
        "clave": "obtener",
        "titulo": "Obtener",
        "pregunta": "¿De dónde salen los datos?",
        "temas": [
            {
                "titulo": "Obtención de datos",
                "resumen": "Scraping web, APIs, volcados y ficheros heredados. Qué se puede recoger y qué obligaciones trae recogerlo.",
                "app": None,
                "minutos": 30,
                "objetivo": "de dónde salen los datos antes de existir, y qué obligaciones trae recogerlos",
            },
            {
                "titulo": "Calidad de datos",
                "resumen": "Cada problema tiene nombre: fechas en cinco formatos, encoding roto, duplicados, huérfanos, ruido en las etiquetas.",
                "app": None,
                "minutos": 45,
                "objetivo": "poner nombre a cada problema de un dataset sucio antes de intentar arreglarlo",
                "enlace": {"texto": "Ver la radiografía de tus datos", "vista": "learn"},
            },
        ],
    },
    {
        "clave": "almacenar",
        "titulo": "Almacenar",
        "pregunta": "¿Dónde los pongo y por qué ahí?",
        "temas": [
            {
                "titulo": "Bases de datos NoSQL",
                "resumen": "Documental y grafo conviviendo. Ninguna base es buena en todo: hay preguntas que solo una de las dos responde bien.",
                "app": "sociallab",
                "minutos": 240,
                "objetivo": "elegir entre documental y grafo según la pregunta, y escribir Cypher sobre un grafo social",
                "bloques": ["basic", "intermediate", "advanced"],
            },
            {
                "titulo": "El data lake: raw → silver → gold",
                "resumen": "Lo que llega tal cual, lo que ya está limpio y lo que está listo para servir. raw es materia prima, gold es lo servible.",
                "app": None,
                "minutos": 30,
                "objetivo": "por qué el dato se organiza en capas y qué va en cada una",
                "enlace": {"texto": "Ver la arquitectura", "vista": "arch"},
            },
        ],
    },
    {
        "clave": "preparar",
        "titulo": "Preparar",
        "pregunta": "¿Cómo los dejo utilizables?",
        "temas": [
            {
                "titulo": "ETL con Spark",
                "resumen": "El pipeline que lleva de raw a gold. Mismo código en tu portátil que en un cluster: cambia la escala, no la lógica.",
                "app": "sociallab",
                "minutos": 180,
                "objetivo": "escribir un pipeline que corra igual en tu portátil y en un cluster",
                "enlace": {"texto": "Lanzar el ETL", "vista": "status"},
            },
            {
                "titulo": "Preprocesamiento (Tema 5)",
                "resumen": "Valores perdidos, outliers, normalización, discretización y reducción. Para cada decisión hay un criterio.",
                "app": "preprolab",
                "minutos": 600,
                "objetivo": "aplicar las técnicas del tema con criterio, y medir si de verdad mejoraron el modelo",
            },
            {
                "titulo": "Datos para modelos de lenguaje",
                "resumen": "Limpiar el corpus, quitar casi-duplicados con MinHash, tokenizar con BPE. Corpus sucio y limpio, mismo modelo.",
                "app": "llmprep",
                "minutos": 300,
                "objetivo": "preparar un corpus y comprobar que la limpieza cambia lo que el modelo aprende",
            },
        ],
    },
    {
        "clave": "explotar",
        "titulo": "Explotar",
        "pregunta": "¿Qué saco de ellos?",
        "temas": [
            {
                "titulo": "Machine Learning",
                "resumen": "Supervisado, no supervisado y sobre grafo, con una fuga de datos puesta a propósito para aprender a olerla.",
                "app": "sociallab",
                "minutos": 180,
                "objetivo": "entrenar sobre datos limpios y detectar cuándo un modelo es sospechosamente bueno",
                "bloques": ["supervised", "unsupervised", "graph_ml"],
            },
            {
                "titulo": "Procesamiento en tiempo real",
                "resumen": "Ventanas, watermarks y estado incremental. Una respuesta correcta que llega tarde es otra forma de estar equivocada.",
                "app": "streamlab",
                "minutos": 300,
                "objetivo": "responder preguntas mientras los datos siguen llegando, y decidir cuánto esperar",
            },
            {
                "titulo": "Visualización y explotación",
                "resumen": "Cómo se cuenta lo que se ha encontrado, y las trampas de representar mal un dato correcto.",
                "app": None,
                "minutos": 30,
                "objetivo": "contar lo que has encontrado sin que la representación mienta",
            },
            {
                "titulo": "Reproducibilidad y gobernanza",
                "resumen": "La lógica vive en el ETL versionado, no en pasos manuales que nadie recuerda. Si no puedes reconstruirlo, no lo controlas.",
                "app": None,
                "minutos": 20,
                "objetivo": "dejar un pipeline que otro pueda volver a ejecutar y obtener lo mismo",
                "enlace": {"texto": "Cómo funciona Quasar", "vista": "arch"},
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
                    "objetivo": tema.get("objetivo")}
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
                    "bloques": [b["key"] for b in bloques],
                })
            else:
                item.update({"app": None, "color": None, "ejercicios": 0})
            temas.append(item)
        salida.append({
            "clave": unidad["clave"], "titulo": unidad["titulo"],
            "pregunta": unidad["pregunta"], "temas": temas,
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
