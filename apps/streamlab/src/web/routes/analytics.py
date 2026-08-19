"""StreamLab — agregador de routers de bloques pedagógicos.

Para cada bloque, decide en tiempo de import si carga la solución
(`<bloque>.py`) o el scaffold (`<bloque>_ex.py`) según LAB_STREAMLAB.

    LAB_STREAMLAB=                  → todo scaffold (alumno)
    LAB_STREAMLAB=windows           → windows resuelto, resto scaffold
    LAB_STREAMLAB=windows,late      → dos bloques resueltos
    LAB_STREAMLAB=all               → todo resuelto

El despacho va por `import_block`, que solo usa la solución si además de
estar desbloqueada existe en disco: en la copia que reciben los alumnos no
se incluye, y entonces se sirve el scaffold en vez de romper el arranque.
"""

from fastapi import APIRouter

from infra.shared.lab_flags import import_block, read_lab_flag

router = APIRouter()

# Bloques del laboratorio, en el orden en que se recorren.
BLOCKS = ["windows", "late", "state"]


def _unlocked() -> set[str]:
    raw = read_lab_flag("LAB_STREAMLAB").strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return set(BLOCKS)
    return {b.strip() for b in raw.split(",") if b.strip()}


_unlocked_blocks = _unlocked()

# Qué se está sirviendo de verdad, que no siempre coincide con el flag: si la
# solución no está en disco (copia de alumnos, o bloque aún sin implementar),
# import_block cae al scaffold aunque el flag diga lo contrario. El estado
# refleja la realidad, no la intención.
_served_solution: dict[str, bool] = {}

for _block in BLOCKS:
    _mod = import_block("src.web.routes", _block, _block in _unlocked_blocks)
    router.include_router(_mod.router)
    _served_solution[_block] = not _mod.__name__.endswith("_ex")


@router.get("/api/streamlab/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques sirven solución.

    `blocks` dice qué se sirve realmente; `flagged` qué pide el flag. Cuando
    difieren es que la solución no está disponible en esta copia.
    """
    return {
        "app": "streamlab",
        "blocks": dict(_served_solution),
        "flagged": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 1,
        "note": "Esqueleto en pie. Próximo: el emisor de telemetría en vivo (fase 2).",
    }
