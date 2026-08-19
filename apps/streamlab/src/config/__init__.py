"""StreamLab — Configuración central.

Re-exporta los valores comunes desde `infra.shared.config_base` y añade los
paths del data lake y flags propios de StreamLab.

Nota sobre los paths: aquí `raw/` no es un volcado histórico como en las
otras apps, sino el **buzón** donde el emisor va dejando micro-lotes de
telemetría y del que Spark lee en streaming. `checkpoints/` por fin se usa:
es donde Structured Streaming recuerda por dónde iba.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga el .env de StreamLab si existe (modo nativo).
_APP_ROOT = Path(__file__).resolve().parent.parent.parent  # apps/streamlab/
_LOCAL_ENV = _APP_ROOT / ".env"
if _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV)

from infra.shared.config_base import (  # noqa: E402
    ENV,
    IS_CLOUD,
    IS_DOCKER,
    IS_LOCAL,
    LOG_LEVEL,
    MONGO_URI,
    QUASAR_ROOT,
    SPARK_MASTER,
    WEB_DEBUG,
    WEB_HOST,
)

# --- Paths específicos de StreamLab ---
_data_lake_env = os.getenv("DATA_LAKE_PATH", "").strip()
DATA_LAKE_PATH: Path = (
    Path(_data_lake_env)
    if _data_lake_env
    else QUASAR_ROOT / "infra" / "data" / "streamlab"
)
# Buzón de entrada: el emisor escribe aquí, Spark lo vigila.
RAW_PATH: Path = DATA_LAKE_PATH / "raw"
SILVER_PATH: Path = DATA_LAKE_PATH / "silver"
GOLD_PATH: Path = DATA_LAKE_PATH / "gold"
# Estado de las consultas de streaming (offsets y agregaciones en curso).
CHECKPOINTS_PATH: Path = DATA_LAKE_PATH / "checkpoints"

# --- MongoDB ---
MONGO_DB: str = os.getenv("MONGO_DB", "streamlab")

# --- Web ---
# Puerto propio (SocialLab 8000, LLM Lab 8001, PreproLab 8002).
WEB_PORT: int = int(os.getenv("WEB_PORT", "8003"))

# --- Parámetros del laboratorio ---
# Umbral de riesgo térmico (°C) que usa la demo del centro de control.
TEMP_ALERTA: float = float(os.getenv("STREAMLAB_TEMP_ALERTA", "75"))
