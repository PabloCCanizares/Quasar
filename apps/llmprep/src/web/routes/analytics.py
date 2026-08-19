"""LLM Lab — agregador de routers de bloques.

Bloques del pipeline de preparación de corpus para LLMs:
  clean     normalización, encoding, HTML strip, length filter
  dedup     near-duplicates (MinHash/LSH) + grafo Neo4j
  tokenize  BPE + shards estilo nanoGPT
  train     nanoGPT + comparativa corpus sucio vs limpio

En Fase 12 (esqueleto) solo expone el estado del lab. Los bloques se
añaden en fases posteriores siguiendo el patrón scaffold/solución de
PreproLab y SocialLab.
"""

import os

from fastapi import APIRouter

from infra.shared.lab_flags import import_block

router = APIRouter()

BLOCKS = ["clean", "dedup", "tokenize", "train"]


def _unlocked() -> set[str]:
    from infra.shared.lab_flags import read_lab_flag
    raw = read_lab_flag("LAB_LLMPREP").strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return set(BLOCKS)
    return {b.strip() for b in raw.split(",") if b.strip()}


_unlocked_blocks = _unlocked()


# Cada bloque: solución si está desbloqueada y presente, si no el scaffold.
#
# Nota sobre train: la solución de train importa funciones de clean.py
# directamente (no el módulo gateado), así que funciona aunque clean siga
# como scaffold. En la distribución sin soluciones no existe ninguno de los
# dos ficheros y ambos caen al scaffold.
# Qué se sirve de verdad, que no siempre coincide con el flag: si la solución
# no está en disco (copia de alumnos), import_block cae al scaffold aunque el
# flag diga lo contrario. El estado refleja la realidad, no la intención.
_served_solution: dict[str, bool] = {}

for _block in BLOCKS:
    _mod = import_block("src.web.routes", _block, _block in _unlocked_blocks)
    router.include_router(_mod.router)
    _served_solution[_block] = not _mod.__name__.endswith("_ex")


@router.get("/api/llmprep/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques sirven solución.

    `blocks` dice qué se sirve realmente; `flagged` qué pide el flag. Cuando
    difieren es que la solución no está disponible en esta copia.
    """
    return {
        "app": "llmprep",
        "blocks": dict(_served_solution),
        "flagged": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 12,
        "note": "Esqueleto inicial. Bloques (clean, dedup, tokenize, train) en construcción.",
    }
