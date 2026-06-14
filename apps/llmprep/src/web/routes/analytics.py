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

router = APIRouter()

BLOCKS = ["clean", "dedup", "tokenize", "train"]


def _unlocked() -> set[str]:
    raw = os.getenv("LAB_LLMPREP", "").strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return set(BLOCKS)
    return {b.strip() for b in raw.split(",") if b.strip()}


_unlocked_blocks = _unlocked()


# --- Bloque clean ---
if "clean" in _unlocked_blocks:
    from src.web.routes import clean as _clean
else:
    from src.web.routes import clean_ex as _clean
router.include_router(_clean.router)

# --- Bloque dedup ---
if "dedup" in _unlocked_blocks:
    from src.web.routes import dedup as _dedup
else:
    from src.web.routes import dedup_ex as _dedup
router.include_router(_dedup.router)


@router.get("/api/llmprep/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques están desbloqueados."""
    return {
        "app": "llmprep",
        "blocks": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 12,
        "note": "Esqueleto inicial. Bloques (clean, dedup, tokenize, train) en construcción.",
    }
