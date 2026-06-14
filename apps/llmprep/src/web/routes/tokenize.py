"""Bloque TOKENIZE — soluciones.

Entrena un tokenizer BPE sobre el corpus limpio y genera los shards
binarios estilo nanoGPT que alimentarán el entrenamiento.

  TOK-1  train       entrena BPE (merges + vocabulario)
  TOK-2  encode      tokeniza un texto de ejemplo
  TOK-3  vocab_stats vocabulario, compresión, tokens más frecuentes
  TOK-4  build_shards codifica el corpus → train.bin / val.bin (uint16)

El tokenizer entrenado se cachea en memoria del proceso para que los
endpoints encode/vocab_stats/build_shards lo reutilicen.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from src.config import GOLD_PATH
from src.web.corpus_loader import load_corpus
from src.tokenize.bpe import BPETokenizer

router = APIRouter(prefix="/api/llmprep/tokenize", tags=["llmprep-tokenize"])

# Cache del tokenizer entrenado
_tokenizer: BPETokenizer | None = None
_train_stats: dict | None = None


def _corpus_texts(limit: int = 2000) -> list[str]:
    docs = load_corpus()
    return [d.get("text", "") for d in docs[:limit]]


# ============================================================
# TOK-1: train
# ============================================================


@router.get("/train")
async def train(
    num_merges: int = Query(500, ge=50, le=2000),
    sample: int = Query(2000, ge=200, le=5500),
) -> dict:
    """TOK-1 — Entrena el tokenizer BPE sobre el corpus."""
    global _tokenizer, _train_stats
    texts = _corpus_texts(sample)
    tok = BPETokenizer()
    stats = tok.train(texts, num_merges=num_merges)
    _tokenizer = tok
    _train_stats = stats
    return {
        "technique": "bpe_train",
        "sample_docs": len(texts),
        **stats,
    }


# ============================================================
# TOK-2: encode
# ============================================================


@router.get("/encode")
async def encode(text: str = Query("la fotosíntesis es un proceso biológico fundamental")) -> dict:
    """TOK-2 — Tokeniza un texto de ejemplo con el BPE entrenado."""
    if _tokenizer is None:
        raise HTTPException(400, detail="Entrena el tokenizer primero (TOK-1).")
    tokens = _tokenizer.encode_tokens(text)
    ids = _tokenizer.encode(text)
    decoded = _tokenizer.decode(ids)
    return {
        "technique": "bpe_encode",
        "input": text,
        "n_chars": len(text),
        "n_tokens": len(ids),
        "tokens": tokens[:60],
        "ids": ids[:60],
        "decoded": decoded,
        "compression_chars_per_token": round(len(text) / max(1, len(ids)), 2),
    }


# ============================================================
# TOK-3: vocab_stats
# ============================================================


@router.get("/vocab_stats")
async def vocab_stats(sample: int = Query(1000, ge=100, le=5500)) -> dict:
    """TOK-3 — Estadísticas del vocabulario + compresión sobre el corpus."""
    if _tokenizer is None:
        raise HTTPException(400, detail="Entrena el tokenizer primero (TOK-1).")
    texts = _corpus_texts(sample)
    total_chars = 0
    total_tokens = 0
    token_freq: Counter = Counter()
    for t in texts:
        total_chars += len(t)
        toks = _tokenizer.encode_tokens(t)
        total_tokens += len(toks)
        token_freq.update(toks)

    most_common = [
        {"token": tk.replace("</w>", "·"), "count": c}
        for tk, c in token_freq.most_common(25)
    ]
    return {
        "technique": "vocab_stats",
        "vocab_size": len(_tokenizer.vocab),
        "num_merges": len(_tokenizer.merges),
        "corpus_chars": total_chars,
        "corpus_tokens": total_tokens,
        "compression_ratio": round(total_chars / max(1, total_tokens), 2),
        "unique_tokens_used": len(token_freq),
        "most_common_tokens": most_common,
    }


# ============================================================
# TOK-4: build_shards
# ============================================================


@router.post("/build_shards")
async def build_shards(
    sample: int = Query(3000, ge=200, le=5500),
    val_fraction: float = Query(0.1, ge=0.01, le=0.3),
) -> dict:
    """TOK-4 — Codifica el corpus a shards binarios estilo nanoGPT.

    Genera train.bin y val.bin (arrays uint16) en gold/, listos para que
    el bloque train los memory-mapee.
    """
    if _tokenizer is None:
        raise HTTPException(400, detail="Entrena el tokenizer primero (TOK-1).")
    texts = _corpus_texts(sample)

    all_ids: list[int] = []
    for t in texts:
        all_ids.extend(_tokenizer.encode(t))

    if len(all_ids) < 100:
        raise HTTPException(400, detail="Muy pocos tokens — aumenta el sample.")

    arr = np.array(all_ids, dtype=np.uint16)
    n_val = int(len(arr) * val_fraction)
    val = arr[:n_val]
    train = arr[n_val:]

    GOLD_PATH.mkdir(parents=True, exist_ok=True)
    train_path = GOLD_PATH / "train.bin"
    val_path = GOLD_PATH / "val.bin"
    train.tofile(str(train_path))
    val.tofile(str(val_path))

    # Guardar también el vocabulario para el decode posterior
    import json
    vocab_path = GOLD_PATH / "vocab.json"
    with open(vocab_path, "w", encoding="utf-8") as f:
        json.dump({
            "vocab": _tokenizer.vocab,
            "merges": [list(m) for m in _tokenizer.merges],
        }, f, ensure_ascii=False)

    return {
        "technique": "build_shards",
        "total_tokens": int(len(arr)),
        "train_tokens": int(len(train)),
        "val_tokens": int(len(val)),
        "vocab_size": len(_tokenizer.vocab),
        "files": {"train": "gold/train.bin", "val": "gold/val.bin", "vocab": "gold/vocab.json"},
        "dtype": "uint16",
        "note": "Estos shards alimentan el bloque train (nanoGPT los memory-mapea).",
    }
