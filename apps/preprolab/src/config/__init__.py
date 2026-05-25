"""PreproLab — Configuración central.

Re-exporta los valores comunes desde `infra.shared.config_base` y añade los
paths del data lake y flags propios de PreproLab.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga el .env de PreproLab si existe (modo nativo).
_APP_ROOT = Path(__file__).resolve().parent.parent.parent  # apps/preprolab/
_LOCAL_ENV = _APP_ROOT / ".env"
if _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV)

from infra.shared.config_base import (  # noqa: E402
    QUASAR_ROOT,
    MONGO_URI,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    SPARK_MASTER,
    WEB_HOST,
    WEB_DEBUG,
    ENV,
    LOG_LEVEL,
    IS_LOCAL,
    IS_DOCKER,
    IS_CLOUD,
)

# --- Paths específicos de PreproLab ---
_data_lake_env = os.getenv("DATA_LAKE_PATH", "").strip()
DATA_LAKE_PATH: Path = (
    Path(_data_lake_env)
    if _data_lake_env
    else QUASAR_ROOT / "infra" / "data" / "preprolab"
)
RAW_PATH: Path = DATA_LAKE_PATH / "raw"
SILVER_PATH: Path = DATA_LAKE_PATH / "silver"
GOLD_PATH: Path = DATA_LAKE_PATH / "gold"
CHECKPOINTS_PATH: Path = DATA_LAKE_PATH / "checkpoints"

# --- MongoDB ---
MONGO_DB: str = os.getenv("MONGO_DB", "preprolab")

# --- Web ---
# Puerto propio de PreproLab (SocialLab usa 8000, LLM Lab usará 8001).
WEB_PORT: int = int(os.getenv("WEB_PORT", "8002"))
