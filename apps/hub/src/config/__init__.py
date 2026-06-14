"""Quasar Hub — configuración.

El Hub no tiene data lake ni Spark. Solo necesita saber:
  - dónde alcanzar las otras 3 apps (URLs internas del compose)
  - dónde está el .env.docker que edita (flags)
  - los nombres de contenedor que reinicia
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

# Catálogo de apps del ecosistema. Cada una con:
#   url_internal: cómo la alcanza el Hub dentro de la red compose
#   url_public:   cómo la abre el usuario en el navegador
#   container:    nombre del contenedor a reiniciar tras cambiar flags
#   status_path:  endpoint de estado de la app
#   flags:        qué variables LAB_* controla y qué bloques tiene cada una
APPS = {
    "sociallab": {
        "name": "SocialLab",
        "tagline": "Red social poliglota",
        "description": "Bases de datos poliglotas (MongoDB + Neo4j), ETL con Spark, grafos sociales y 6 modelos de Machine Learning.",
        "url_internal": "http://app-sociallab:8000",
        "url_public": "http://localhost:8000",
        "container": "quasar-sociallab",
        "status_path": "/api/analytics/lab/status",
        "color": "#1da1f2",
        "flags": {
            "LAB_NEO4J": ["basic", "intermediate", "advanced"],
            "LAB_ML": ["supervised", "unsupervised", "graph_ml"],
        },
    },
    "preprolab": {
        "name": "PreproLab",
        "tagline": "Preprocesamiento (Tema 5)",
        "description": "Las 8 técnicas del Tema 5 sobre una flota de robots: missing, outliers, integración, transformación, normalización, reducción + Pipeline Studio.",
        "url_internal": "http://app-preprolab:8002",
        "url_public": "http://localhost:8002",
        "container": "quasar-preprolab",
        "status_path": "/api/preprolab/lab/status",
        "color": "#1d9bf0",
        "flags": {
            "LAB_PREPROLAB": ["eda", "missing", "outliers", "integration",
                              "transform", "normalize", "reduce_dim", "reduce_inst"],
        },
    },
    "llmprep": {
        "name": "LLM Lab",
        "tagline": "Corpus para LLMs",
        "description": "Preparación de corpus para modelos de lenguaje: limpieza, deduplicación (MinHash + Neo4j), tokenización BPE y entrenamiento con demo sucio vs limpio.",
        "url_internal": "http://app-llmprep:8001",
        "url_public": "http://localhost:8001",
        "container": "quasar-llmprep",
        "status_path": "/api/llmprep/lab/status",
        "color": "#a78bfa",
        "flags": {
            "LAB_LLMPREP": ["clean", "dedup", "tokenize", "train"],
        },
    },
}
