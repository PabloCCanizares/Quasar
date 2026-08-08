"""Configuración base compartida por todas las apps de Quasar.

Lee variables de entorno con defaults razonables. Las apps importan de aquí
las claves comunes (MongoDB, Neo4j, Spark, Web, entorno) y añaden encima sus
paths específicos del data lake.

Carga de `.env`:
  - Cada app puede invocar `load_dotenv()` antes de importar este módulo si
    necesita un `.env` propio. Aquí solo se llama si no hay nada cargado todavía.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Solo carga .env si aún no hay variables clave en el entorno.
# Las apps pueden hacer su propio load_dotenv() apuntando al .env de su carpeta.
if not os.getenv("MONGO_URI"):
    load_dotenv()

# --- Raíz del repo (Quasar/) ---
# Este archivo vive en infra/shared/config_base.py → parents[2] = raíz del repo.
QUASAR_ROOT: Path = Path(__file__).resolve().parents[2]

# --- MongoDB ---
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# --- Neo4j ---
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

# --- Spark ---
SPARK_MASTER: str = os.getenv("SPARK_MASTER", "local[*]")

# --- Web ---
WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
WEB_DEBUG: bool = os.getenv("WEB_DEBUG", "true").lower() == "true"

# --- General ---
ENV: str = os.getenv("ENV", "local")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
IS_LOCAL: bool = ENV == "local"
IS_DOCKER: bool = ENV == "docker"
IS_CLOUD: bool = ENV == "cloud"
