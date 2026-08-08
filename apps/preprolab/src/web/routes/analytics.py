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

from infra.shared.lab_flags import import_block

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
    from infra.shared.lab_flags import read_lab_flag
    raw = read_lab_flag("LAB_PREPROLAB").strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return set(BLOCKS)
    return {b.strip() for b in raw.split(",") if b.strip()}


_unlocked_blocks = _unlocked()


# Cada bloque: solución si está desbloqueada y presente, si no el scaffold.
for _block in BLOCKS:
    router.include_router(
        import_block("src.web.routes", _block, _block in _unlocked_blocks).router
    )


@router.get("/api/preprolab/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques están desbloqueados."""
    return {
        "app": "preprolab",
        "blocks": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 10,
        "note": "Todos los 8 bloques del Tema 5 implementados. Próximo: Pipeline Studio (hito final).",
    }
