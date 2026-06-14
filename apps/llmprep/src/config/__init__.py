"""LLM Lab — Configuración central.

Re-exporta de infra.shared.config_base y añade paths + flags propios.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_APP_ROOT = Path(__file__).resolve().parent.parent.parent  # apps/llmprep/
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

# --- Paths específicos de LLM Lab ---
_data_lake_env = os.getenv("DATA_LAKE_PATH", "").strip()
DATA_LAKE_PATH: Path = (
    Path(_data_lake_env)
    if _data_lake_env
    else QUASAR_ROOT / "infra" / "data" / "llmprep"
)
RAW_PATH: Path = DATA_LAKE_PATH / "raw"
SILVER_PATH: Path = DATA_LAKE_PATH / "silver"
GOLD_PATH: Path = DATA_LAKE_PATH / "gold"
CHECKPOINTS_PATH: Path = DATA_LAKE_PATH / "checkpoints"

# --- MongoDB ---
MONGO_DB: str = os.getenv("MONGO_DB", "llmprep")

# --- Web ---
WEB_PORT: int = int(os.getenv("WEB_PORT", "8001"))
