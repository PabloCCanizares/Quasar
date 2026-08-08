"""Cargador del corpus en memoria (con caché por proceso).

El corpus (~5450 docs, ~7 MB) cabe de sobra en RAM. Lo cargamos una vez
y lo cacheamos. Si se regenera el corpus, reinicia el contenedor.

Fuente de datos, por orden de preferencia:
  1. Capa **silver** (parquet) escrita por el ETL Spark (`src.spark.run_pipeline`).
  2. Capa **raw** (`corpus.json`, JSON Lines) del ingest, como fallback.

La suciedad se preserva idéntica en ambas capas (el ETL ingesta, no limpia),
así que los bloques clean/dedup/tokenize funcionan igual lean de donde lean.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from src.config import RAW_PATH, SILVER_PATH

_cache: Optional[list[dict]] = None


def _clean_value(v):
    """Normaliza valores venidos de parquet a tipos Python nativos.

    pandas/pyarrow devuelven arrays numpy (p.ej. `_noise`) y NaN para nulls;
    los endpoints esperan listas y None como el JSON crudo.
    """
    if v is None:
        return None
    # numpy arrays (columna `_noise`: array<string>) → list.
    if hasattr(v, "tolist") and not isinstance(v, (str, bytes)):
        return v.tolist()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _read_silver() -> Optional[list[dict]]:
    """Lee el corpus desde la capa silver (parquet) si el ETL ya lo generó."""
    silver_dir: Path = SILVER_PATH / "corpus"
    if not (silver_dir.is_dir() and any(silver_dir.glob("*.parquet"))):
        return None
    import pandas as pd  # import perezoso: solo si hay silver

    df = pd.read_parquet(silver_dir)
    return [{k: _clean_value(v) for k, v in rec.items()} for rec in df.to_dict(orient="records")]


def _read_raw() -> list[dict]:
    """Lee el corpus desde `corpus.json` (JSON Lines). Fallback si no hay silver."""
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
    return docs


def load_corpus() -> list[dict]:
    """Carga el corpus (silver parquet o raw JSON) y lo cachea."""
    global _cache
    if _cache is not None:
        return _cache
    docs = _read_silver()
    if docs is None:
        docs = _read_raw()
    _cache = docs
    return docs


def clear_cache() -> None:
    global _cache
    _cache = None


def is_ingested() -> bool:
    """True si hay corpus en disco (en silver parquet o raw JSON)."""
    silver_dir = SILVER_PATH / "corpus"
    return silver_dir.is_dir() or (RAW_PATH / "corpus.json").exists()
