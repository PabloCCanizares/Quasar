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
    from infra.shared.lab_flags import read_lab_flag
    raw = read_lab_flag("LAB_LLMPREP").strip().lower()
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

# --- Bloque tokenize ---
if "tokenize" in _unlocked_blocks:
    from src.web.routes import tokenize as _tokenize
else:
    from src.web.routes import tokenize_ex as _tokenize
router.include_router(_tokenize.router)

# --- Bloque train ---
# Nota: train (solución) importa funciones de clean (solución). Si se
# desbloquea train sin clean, igualmente funciona porque importa el módulo
# clean.py directamente, no el gateado.
if "train" in _unlocked_blocks:
    from src.web.routes import train as _train
else:
    from src.web.routes import train_ex as _train
router.include_router(_train.router)


@router.get("/api/llmprep/lab/status")
async def lab_status():
    """Estado actual del laboratorio: qué bloques están desbloqueados."""
    return {
        "app": "llmprep",
        "blocks": {b: (b in _unlocked_blocks) for b in BLOCKS},
        "phase": 12,
        "note": "Esqueleto inicial. Bloques (clean, dedup, tokenize, train) en construcción.",
    }
