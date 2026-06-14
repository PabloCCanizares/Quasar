"""Cargador del corpus en memoria (con caché por proceso).

El corpus (~5450 docs, ~7 MB) cabe de sobra en RAM. Lo cargamos una vez
y lo cacheamos. Si se regenera el corpus, reinicia el contenedor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.config import RAW_PATH

_cache: Optional[list[dict]] = None


def load_corpus() -> list[dict]:
    """Carga corpus.json (JSON Lines) y lo cachea."""
    global _cache
    if _cache is not None:
        return _cache
    path: Path = RAW_PATH / "corpus.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encuentra {path}. Ejecuta `./lab.sh llmprep ingest`."
        )
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    _cache = docs
    return docs


def clear_cache() -> None:
    global _cache
    _cache = None


def is_ingested() -> bool:
    return (RAW_PATH / "corpus.json").exists()
