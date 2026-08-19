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
# Qué se sirve de verdad, que no siempre coincide con el flag: si la solución
# no está en disco (copia de alumnos), import_block cae al scaffold aunque el
# flag diga lo contrario. El estado refleja la realidad, no la intención.
_served_solution: dict[str, bool] = {}

for _block in BLOCKS:
    _mod = import_block("src.web.routes", _block, _block in _unlocked_blocks)
    router.include_router(_mod.router)
    _served_solution[_block] = not _mod.__name__.endswith("_ex")


@router.get("/api/preprolab/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques sirven solución.

    `blocks` dice qué se sirve realmente; `flagged` qué pide el flag. Cuando
    difieren es que la solución no está disponible en esta copia.
    """
    return {
        "app": "preprolab",
        "blocks": dict(_served_solution),
        "flagged": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 10,
        "note": "Todos los 8 bloques del Tema 5 implementados. Próximo: Pipeline Studio (hito final).",
    }
