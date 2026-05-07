"""
SocialLab — Configuración central.

Toda la aplicación lee de aquí. Nunca se hardcodea un URI, ruta o credencial.
Para migrar a cloud: edita .env, no toques código.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_LAKE_PATH = Path(os.getenv("DATA_LAKE_PATH", PROJECT_ROOT / "data"))
RAW_PATH = DATA_LAKE_PATH / "raw"
SILVER_PATH = DATA_LAKE_PATH / "silver"
GOLD_PATH = DATA_LAKE_PATH / "gold"

# --- MongoDB ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "sociallab")

# --- Neo4j ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# --- Spark ---
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")

# --- Web ---
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
WEB_DEBUG = os.getenv("WEB_DEBUG", "true").lower() == "true"

# --- General ---
ENV = os.getenv("ENV", "local")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
IS_LOCAL = ENV == "local"
