"""PreproLab — agregador de routers de bloques pedagógicos.

Para cada bloque del Tema 5, decide en tiempo de import si carga la solución
oficial (`<bloque>.py`) o el scaffold (`<bloque>_ex.py`) según la variable
de entorno LAB_PREPROLAB (lista separada por comas con los bloques
desbloqueados).

Ejemplos:
    LAB_PREPROLAB=                       → todo scaffold (alumno)
    LAB_PREPROLAB=eda                    → EDA resuelto, resto scaffold
    LAB_PREPROLAB=eda,missing            → EDA + missing resueltos
    LAB_PREPROLAB=all                    → todo resuelto

Cada vez que se cambia el flag con `./lab.sh preprolab unlock|lock`, el
script reinicia el contenedor app-preprolab para que esta selección se
vuelva a evaluar.
"""

import os

from fastapi import APIRouter

router = APIRouter()

# Bloques pedagógicos del Tema 5 (orden temporal del pipeline).
BLOCKS = [
    "eda",
    "missing",
    "outliers",
    "integration",
    "transform",
    "normalize",
    "reduce_dim",
    "reduce_inst",
]


def _unlocked() -> set[str]:
    raw = os.getenv("LAB_PREPROLAB", "").strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return set(BLOCKS)
    return {b.strip() for b in raw.split(",") if b.strip()}


_unlocked_blocks = _unlocked()


# --- Bloque eda ---
if "eda" in _unlocked_blocks:
    from src.web.routes import eda as _eda
else:
    from src.web.routes import eda_ex as _eda
router.include_router(_eda.router)

# --- Bloque missing ---
if "missing" in _unlocked_blocks:
    from src.web.routes import missing as _missing
else:
    from src.web.routes import missing_ex as _missing
router.include_router(_missing.router)

# Los otros bloques se irán incluyendo en sus fases:
#   if "outliers" in _unlocked_blocks: from src.web.routes import outliers
#   ...


@router.get("/api/preprolab/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques están desbloqueados."""
    return {
        "app": "preprolab",
        "blocks": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 4,
        "note": "Bloques implementados: eda, missing. Próximos: outliers, integration, ...",
    }
