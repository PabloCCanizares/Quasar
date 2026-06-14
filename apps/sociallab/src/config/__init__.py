"""SocialLab — Configuración central.

Re-exporta los valores comunes desde `infra.shared.config_base` y añade los
paths del data lake propios de SocialLab. Toda la aplicación lee de aquí.

Para migrar a cloud: edita el `.env` correspondiente, no toques código.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga el .env de SocialLab (apps/sociallab/.env) si existe.
# Debe ocurrir ANTES de importar config_base para que las variables estén ya
# en el entorno cuando shared lea sus defaults.
_APP_ROOT = Path(__file__).resolve().parent.parent.parent  # apps/sociallab/
_LOCAL_ENV = _APP_ROOT / ".env"
if _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV)

# Re-exporta valores comunes desde shared.
from infra.shared.config_base import (  # noqa: E402
    ENV,
    IS_CLOUD,
    IS_DOCKER,
    IS_LOCAL,
    LOG_LEVEL,
    MONGO_URI,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    QUASAR_ROOT,
    SPARK_MASTER,
    WEB_DEBUG,
    WEB_HOST,
)

# --- Paths específicos de SocialLab ---
# Default: <repo>/infra/data/sociallab.
# Override: DATA_LAKE_PATH en .env (Docker usa /app/data dentro del container).
# Si la variable está vacía o no definida, cae al default Quasar.
_data_lake_env = os.getenv("DATA_LAKE_PATH", "").strip()
DATA_LAKE_PATH: Path = (
    Path(_data_lake_env)
    if _data_lake_env
    else QUASAR_ROOT / "infra" / "data" / "sociallab"
)
RAW_PATH: Path = DATA_LAKE_PATH / "raw"
SILVER_PATH: Path = DATA_LAKE_PATH / "silver"
GOLD_PATH: Path = DATA_LAKE_PATH / "gold"

# --- MongoDB ---
# El URI viene de shared. La BD es propia de la app.
MONGO_DB: str = os.getenv("MONGO_DB", "sociallab")

# --- Web ---
# Puerto propio de SocialLab (preprolab usará 8002, llmprep 8001).
WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))
