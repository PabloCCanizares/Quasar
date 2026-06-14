"""Bloque TRAIN — soluciones.

Entrena un modelo de lenguaje sobre el corpus y demuestra el impacto de
la limpieza: mismo modelo entrenado sobre corpus SUCIO vs LIMPIO.

  TRAIN-1  train       entrena el modelo, reporta perplexity
  TRAIN-2  generate    muestrea texto del modelo entrenado
  TRAIN-3  compare     LA DEMO: sucio vs limpio (perplexity + generación)

Usa un n-gram LM (src/train/ngram_lm.py) para que entrene en <1s sin
PyTorch. El pipeline (shards → train → sample → comparar) es idéntico al
de nanoGPT; para un Transformer real el alumno cambiaría la clase del
modelo manteniendo la interfaz.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.web.corpus_loader import load_corpus
from src.train.ngram_lm import NgramLM

# Reutilizamos las funciones de limpieza del bloque clean (solución)
from src.web.routes.clean import fix_encoding, strip_html, detect_language, redact_pii

router = APIRouter(prefix="/api/llmprep/train", tags=["llmprep-train"])

_model: NgramLM | None = None


def _clean_text(text: str) -> str:
    text = fix_encoding(text)
    text = strip_html(text)
    text, _ = redact_pii(text)
    return text


def _split(texts: list[str], val_frac: float = 0.1) -> tuple[list[str], list[str]]:
    n_val = max(1, int(len(texts) * val_frac))
    return texts[n_val:], texts[:n_val]


# ============================================================
# TRAIN-1: train
# ============================================================


@router.get("/train")
async def train_endpoint(
    n: int = Query(3, ge=2, le=4),
    sample: int = Query(3000, ge=200, le=5500),
) -> dict:
    """TRAIN-1 — Entrena el modelo de lenguaje sobre el corpus limpio."""
    global _model
    docs = load_corpus()[:sample]
    texts = [_clean_text(d.get("text", "")) for d in docs]
    texts = [t for t in texts if len(t) > 50 and detect_language(t) != "en"]
    train_texts, val_texts = _split(texts)

    model = NgramLM(n=n)
    stats = model.train(train_texts)
    ppl = model.perplexity(val_texts)
    _model = model

    return {
        "technique": "ngram_train",
        "model": f"{n}-gram LM con backoff",
        "train_docs": len(train_texts),
        "val_docs": len(val_texts),
        **stats,
        "val_perplexity": round(ppl, 2),
        "note": "Perplexity más baja = mejor modelo. Compara con TRAIN-3 (sucio vs limpio).",
    }


# ============================================================
# TRAIN-2: generate
# ============================================================


@router.get("/generate")
async def generate_endpoint(
    prompt: str = Query("la"),
    max_tokens: int = Query(40, ge=5, le=150),
    temperature: float = Query(0.8, ge=0.1, le=2.0),
) -> dict:
    """TRAIN-2 — Genera texto muestreando del modelo entrenado."""
    if _model is None:
        raise HTTPException(400, detail="Entrena el modelo primero (TRAIN-1).")
    text = _model.generate(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
    return {
        "technique": "generate",
        "prompt": prompt,
        "temperature": temperature,
        "generated": text,
    }


# ============================================================
# TRAIN-3: compare dirty vs clean (LA DEMO)
# ============================================================


@router.get("/compare")
async def compare_endpoint(
    n: int = Query(3, ge=2, le=4),
    sample: int = Query(3000, ge=200, le=5500),
    prompt: str = Query("la"),
) -> dict:
    """TRAIN-3 — Compara modelo entrenado sobre corpus SUCIO vs LIMPIO.

    Entrena dos modelos idénticos: uno sobre el corpus crudo (con HTML,
    mojibake, gibberish, otros idiomas) y otro sobre el corpus limpio.
    Compara perplexity y muestra una generación de cada uno.

    La conclusión pedagógica: el modelo sucio aprende a generar basura
    (HTML, mojibake); el limpio genera español coherente. La calidad del
    corpus determina la calidad del modelo.
    """
    docs = load_corpus()[:sample]

    # Validación común: textos LIMPIOS (la referencia justa)
    clean_all = [_clean_text(d.get("text", "")) for d in docs]
    clean_all = [t for t in clean_all if len(t) > 50 and detect_language(t) != "en"]
    _, val_texts = _split(clean_all)

    # Modelo SUCIO: entrena sobre el texto crudo tal cual
    dirty_texts = [d.get("text", "") for d in docs]
    dirty_train, _ = _split(dirty_texts)
    dirty_model = NgramLM(n=n)
    dirty_model.train(dirty_train)

    # Modelo LIMPIO: entrena sobre el texto limpio
    clean_train, _ = _split(clean_all)
    clean_model = NgramLM(n=n)
    clean_model.train(clean_train)

    dirty_ppl = dirty_model.perplexity(val_texts)
    clean_ppl = clean_model.perplexity(val_texts)

    return {
        "technique": "compare_dirty_vs_clean",
        "model": f"{n}-gram LM",
        "validation_set": "corpus limpio (referencia justa para ambos)",
        "dirty": {
            "train_docs": len(dirty_train),
            "vocab_size": len(dirty_model.vocab),
            "perplexity": round(dirty_ppl, 2),
            "generated": dirty_model.generate(prompt=prompt, max_tokens=40, temperature=0.8),
        },
        "clean": {
            "train_docs": len(clean_train),
            "vocab_size": len(clean_model.vocab),
            "perplexity": round(clean_ppl, 2),
            "generated": clean_model.generate(prompt=prompt, max_tokens=40, temperature=0.8),
        },
        "perplexity_improvement_pct": round(100 * (dirty_ppl - clean_ppl) / dirty_ppl, 1) if dirty_ppl else 0,
        "conclusion": (
            "El modelo entrenado sobre el corpus LIMPIO tiene menor perplexity "
            "y genera texto más coherente. El vocabulario del modelo sucio está "
            "inflado con tokens de HTML, mojibake y otros idiomas que el modelo "
            "aprende a reproducir. La calidad del corpus determina la del modelo."
        ),
    }
