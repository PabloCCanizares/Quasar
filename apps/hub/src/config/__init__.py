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
        "tasks": {"seed": "Generar datos sucios", "etl": "ETL Spark → Mongo + Neo4j"},
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
        "tech": ["pandas", "scikit-learn", "Plotly", "FastAPI"],
        "tasks": {"seed": "Generar flota de robots"},
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
        "tech": ["MinHash/LSH", "Neo4j", "BPE", "n-gram LM", "FastAPI"],
        "tasks": {"ingest": "Generar corpus sucio"},
        "uses_neo4j": True,
        "uses_mongo": True,
        "blocks": [
            {"flag": "LAB_LLMPREP", "key": "clean", "label": "Clean", "desc": "fix encoding, strip HTML, filtro longitud/idioma, PII removal", "exercises": 6},
            {"flag": "LAB_LLMPREP", "key": "dedup", "label": "Dedup", "desc": "exact, MinHash, LSH + grafo SIMILAR_TO en Neo4j + Cypher", "exercises": 5},
            {"flag": "LAB_LLMPREP", "key": "tokenize", "label": "Tokenize", "desc": "BPE desde cero + shards .bin estilo nanoGPT", "exercises": 4},
            {"flag": "LAB_LLMPREP", "key": "train", "label": "Train ★", "desc": "Modelo de lenguaje + demo sucio vs limpio (perplexity)", "exercises": 3},
        ],
    },
}


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
