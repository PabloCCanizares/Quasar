"""Bloque CLEAN — soluciones.

Limpieza del corpus crudo. Cada endpoint aplica UNA técnica y reporta
cuántos documentos modificó/eliminó, validando contra el ground truth
`_noise` (que en un corpus real no existiría).

  CLEAN-1  fix_encoding    repara mojibake (Ã¡ → á)
  CLEAN-2  strip_html      elimina <ref>, {{cite}}, [[wikilinks]], tags,
                           boilerplate (Véase también, Referencias...)
  CLEAN-3  length_filter   descarta docs demasiado cortos o largos
  CLEAN-4  language_filter detecta y descarta docs que no son español
  CLEAN-5  pii_removal     tacha emails y teléfonos
  CLEAN-6  pipeline        aplica las 5 y mide reducción + precision/recall
                           contra el ground truth

Endpoint no-gateado: corpus_stats (siempre disponible).
"""

from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, HTTPException, Query

from src.web.corpus_loader import is_ingested, load_corpus

router = APIRouter(prefix="/api/llmprep/clean", tags=["llmprep-clean"])


# ============================================================
# Helpers de limpieza (reutilizados por pipeline)
# ============================================================

_MOJIBAKE_MAP = {
    "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
    "Ã±": "ñ", "Ã¼": "ü", "Â¿": "¿", "Â¡": "¡", "Ã‘": "Ñ",
}

_BOILERPLATE_MARKERS = [
    "== Véase también ==", "== Referencias ==", "== Enlaces externos ==",
    "Categorías:", "Este artículo es un esbozo",
]

# Stopwords frecuentes en español para detección heurística de idioma
_ES_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "que", "en", "y",
    "a", "con", "por", "para", "su", "se", "es", "como", "más", "o", "lo",
    "este", "esta", "entre", "sin", "sobre", "cuando", "también",
}
_EN_STOPWORDS = {
    "the", "of", "and", "to", "in", "is", "that", "for", "with", "this",
    "are", "as", "be", "by", "an", "have", "has", "was", "which", "their",
}


def fix_encoding(text: str) -> str:
    for k, v in _MOJIBAKE_MAP.items():
        text = text.replace(k, v)
    return text


def strip_html(text: str) -> str:
    # [[link|text]] -> text  (conserva el texto visible)
    text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)
    # [[link]] -> link
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # <ref>...</ref> y <ref/>
    text = re.sub(r"<ref[^>]*>.*?</ref>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^>]*/>", " ", text)
    # {{cite ...}}, {{Ficha...}}
    text = re.sub(r"\{\{[^}]*\}\}", " ", text)
    # comentarios HTML
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    # cualquier otra etiqueta HTML
    text = re.sub(r"<[^>]+>", " ", text)
    # Quitar bloques boilerplate (desde el marcador hasta el final del doc)
    for marker in _BOILERPLATE_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    # Normalizar espacios
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def detect_language(text: str) -> str:
    """Heurística simple: cuenta stopwords ES vs EN. Devuelve 'es', 'en' o 'unknown'."""
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < 5:
        return "unknown"
    es = sum(1 for w in words if w in _ES_STOPWORDS)
    en = sum(1 for w in words if w in _EN_STOPWORDS)
    if es == 0 and en == 0:
        return "unknown"
    return "es" if es >= en else "en"


def redact_pii(text: str) -> tuple[str, int]:
    """Tacha emails y teléfonos. Devuelve (texto, n_redacciones)."""
    n = 0
    def _email_sub(m):
        nonlocal n
        n += 1
        return "[EMAIL]"
    def _phone_sub(m):
        nonlocal n
        n += 1
        return "[TELEFONO]"
    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", _email_sub, text)
    text = re.sub(r"\+?\d[\d\s]{7,}\d", _phone_sub, text)
    return text, n


# ============================================================
# Endpoint no-gateado: estadísticas del corpus
# ============================================================


@router.get("/corpus_stats")
async def corpus_stats() -> dict:
    """Resumen del corpus crudo: tamaño, distribución de ruido (ground truth)."""
    if not is_ingested():
        raise HTTPException(503, detail="Corpus no generado. Ejecuta `./lab.sh llmprep ingest`.")
    docs = load_corpus()
    from collections import Counter
    noise_counter: Counter = Counter()
    total_chars = 0
    for d in docs:
        total_chars += d.get("char_count", len(d.get("text", "")))
        for n in d.get("_noise", []):
            noise_counter[n] += 1
    clean_docs = sum(1 for d in docs if not d.get("_noise"))
    return {
        "n_docs": len(docs),
        "total_chars": total_chars,
        "avg_chars": round(total_chars / len(docs), 1) if docs else 0,
        "clean_docs": clean_docs,
        "noisy_docs": len(docs) - clean_docs,
        "noise_distribution": dict(noise_counter),
    }


# ============================================================
# CLEAN-1: fix_encoding
# ============================================================


@router.get("/fix_encoding")
async def fix_encoding_endpoint() -> dict:
    """CLEAN-1 — Repara mojibake en todo el corpus."""
    docs = load_corpus()
    affected = 0
    examples = []
    for d in docs:
        original = d.get("text", "")
        fixed = fix_encoding(original)
        if fixed != original:
            affected += 1
            if len(examples) < 5:
                examples.append({
                    "id": d["id"],
                    "before": original[:80],
                    "after": fixed[:80],
                })
    # Ground truth: docs marcados con broken_encoding
    truth = sum(1 for d in docs if "broken_encoding" in d.get("_noise", []))
    return {
        "technique": "fix_encoding",
        "docs_modified": affected,
        "ground_truth_broken_encoding": truth,
        "examples": examples,
    }


# ============================================================
# CLEAN-2: strip_html
# ============================================================


@router.get("/strip_html")
async def strip_html_endpoint() -> dict:
    """CLEAN-2 — Elimina HTML residual + boilerplate."""
    docs = load_corpus()
    affected = 0
    chars_removed = 0
    examples = []
    for d in docs:
        original = d.get("text", "")
        stripped = strip_html(original)
        if stripped != original:
            affected += 1
            chars_removed += len(original) - len(stripped)
            if len(examples) < 5:
                examples.append({
                    "id": d["id"],
                    "chars_before": len(original),
                    "chars_after": len(stripped),
                    "removed_snippet": original[:120],
                })
    truth = sum(1 for d in docs if "html_residual" in d.get("_noise", []) or "boilerplate" in d.get("_noise", []))
    return {
        "technique": "strip_html",
        "docs_modified": affected,
        "total_chars_removed": chars_removed,
        "ground_truth_html_or_boilerplate": truth,
        "examples": examples,
    }


# ============================================================
# CLEAN-3: length_filter
# ============================================================


@router.get("/length_filter")
async def length_filter_endpoint(
    min_chars: int = Query(200, ge=0),
    max_chars: int = Query(15000, ge=100),
) -> dict:
    """CLEAN-3 — Descarta documentos demasiado cortos o largos."""
    docs = load_corpus()
    too_short = [d for d in docs if len(d.get("text", "")) < min_chars]
    too_long = [d for d in docs if len(d.get("text", "")) > max_chars]
    kept = len(docs) - len(too_short) - len(too_long)
    truth_short = sum(1 for d in docs if "too_short" in d.get("_noise", []))
    truth_long = sum(1 for d in docs if "too_long" in d.get("_noise", []))
    return {
        "technique": "length_filter",
        "min_chars": min_chars,
        "max_chars": max_chars,
        "n_docs": len(docs),
        "dropped_too_short": len(too_short),
        "dropped_too_long": len(too_long),
        "kept": kept,
        "ground_truth_too_short": truth_short,
        "ground_truth_too_long": truth_long,
    }


# ============================================================
# CLEAN-4: language_filter
# ============================================================


@router.get("/language_filter")
async def language_filter_endpoint(
    target_lang: str = Query("es"),
) -> dict:
    """CLEAN-4 — Detecta idioma y descarta los que no son el objetivo."""
    docs = load_corpus()
    detected = {"es": 0, "en": 0, "unknown": 0}
    dropped = []
    for d in docs:
        lang = detect_language(d.get("text", ""))
        detected[lang] = detected.get(lang, 0) + 1
        if lang != target_lang and lang != "unknown":
            dropped.append(d)
    truth = sum(1 for d in docs if "wrong_lang" in d.get("_noise", []))
    # Precisión: de los que detectamos como no-target, cuántos eran realmente wrong_lang
    tp = sum(1 for d in dropped if "wrong_lang" in d.get("_noise", []))
    precision = round(tp / len(dropped), 3) if dropped else 0.0
    recall = round(tp / truth, 3) if truth else 0.0
    return {
        "technique": "language_filter",
        "target_lang": target_lang,
        "detected_distribution": detected,
        "dropped": len(dropped),
        "ground_truth_wrong_lang": truth,
        "precision": precision,
        "recall": recall,
    }


# ============================================================
# CLEAN-5: pii_removal
# ============================================================


@router.get("/pii_removal")
async def pii_removal_endpoint() -> dict:
    """CLEAN-5 — Tacha emails y teléfonos."""
    docs = load_corpus()
    affected = 0
    total_redactions = 0
    examples = []
    for d in docs:
        _, n = redact_pii(d.get("text", ""))
        if n > 0:
            affected += 1
            total_redactions += n
            if len(examples) < 5:
                redacted, _ = redact_pii(d.get("text", ""))
                examples.append({"id": d["id"], "snippet": redacted[-100:]})
    truth = sum(1 for d in docs if "pii" in d.get("_noise", []))
    return {
        "technique": "pii_removal",
        "docs_with_pii": affected,
        "total_redactions": total_redactions,
        "ground_truth_pii": truth,
        "examples": examples,
    }


# ============================================================
# CLEAN-6: pipeline (todas las técnicas)
# ============================================================


@router.get("/pipeline")
async def pipeline_endpoint(
    min_chars: int = Query(200),
    max_chars: int = Query(15000),
    target_lang: str = Query("es"),
) -> dict:
    """CLEAN-6 — Aplica las 5 técnicas en orden y reporta la reducción total."""
    docs = load_corpus()
    n_initial = len(docs)
    chars_initial = sum(len(d.get("text", "")) for d in docs)

    cleaned = []
    for d in docs:
        text = d.get("text", "")
        # 1. encoding
        text = fix_encoding(text)
        # 2. html + boilerplate
        text = strip_html(text)
        # 3. pii
        text, _ = redact_pii(text)
        # 4. length filter
        if len(text) < min_chars or len(text) > max_chars:
            continue
        # 5. language filter
        lang = detect_language(text)
        if lang == "en":  # solo descartamos los claramente en otro idioma
            continue
        cleaned.append({**d, "text": text})

    chars_final = sum(len(d["text"]) for d in cleaned)
    return {
        "technique": "pipeline (las 5 técnicas)",
        "docs_initial": n_initial,
        "docs_final": len(cleaned),
        "docs_dropped": n_initial - len(cleaned),
        "chars_initial": chars_initial,
        "chars_final": chars_final,
        "chars_reduction_pct": round(100 * (chars_initial - chars_final) / chars_initial, 2) if chars_initial else 0,
        "docs_reduction_pct": round(100 * (n_initial - len(cleaned)) / n_initial, 2) if n_initial else 0,
        "note": (
            "El corpus limpio resultante es el que alimentaría el bloque dedup "
            "y, posteriormente, la tokenización y el entrenamiento del modelo."
        ),
    }
