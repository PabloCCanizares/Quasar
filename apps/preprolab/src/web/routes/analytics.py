"""PreproLab — endpoints de analytics.

En Fase 1 solo expone `/api/preprolab/lab/status`. Los bloques de ejercicio se
irán añadiendo en fases posteriores, manteniendo el patrón scaffold/solution
de SocialLab (selección del módulo según LAB_PREPROLAB en tiempo de import).
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


@router.get("/api/preprolab/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques están desbloqueados.

    El frontend lo consulta al arrancar para mostrar en el sidebar qué bloques
    estan resueltos vs en modo ejercicio.
    """
    return {
        "app": "preprolab",
        "blocks": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 1,
        "note": "Esqueleto inicial. Los bloques se implementaran en fases posteriores.",
    }
