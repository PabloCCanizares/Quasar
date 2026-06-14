"""Bloque CLEAN — scaffolds (versión alumno).

Seis ejercicios de limpieza de corpus. Cada endpoint aplica una técnica
y se valida contra el ground truth `_noise` del corpus.

  CLEAN-1  fix_encoding    repara mojibake (Ã¡ → á)
  CLEAN-2  strip_html      quita <ref>, {{cite}}, [[wikilinks]], boilerplate
  CLEAN-3  length_filter   descarta docs muy cortos/largos
  CLEAN-4  language_filter detecta idioma y descarta no-español
  CLEAN-5  pii_removal     tacha emails/teléfonos
  CLEAN-6  pipeline        aplica las 5 + mide reducción

Endpoint no-ejercicio (corpus_stats) se sirve siempre desde clean.py.

Flujo:
  1. Implementa las funciones aquí.
  2. ./lab.sh llmprep restart
  3. Recarga la pestaña Clean.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.web.corpus_loader import is_ingested, load_corpus

router = APIRouter(prefix="/api/llmprep/clean", tags=["llmprep-clean"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {"error": "scaffold", "exercise": exercise, "hint": hint, "available": False}


@router.get("/corpus_stats")
async def corpus_stats() -> dict:
    """No es ejercicio — se sirve siempre."""
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


@router.get("/fix_encoding")
async def fix_encoding_endpoint() -> dict:
    """
    EJERCICIO CLEAN-1 — Repara mojibake en todo el corpus.

    El mojibake aparece cuando UTF-8 se decodifica como Latin-1: 'á' se
    convierte en 'Ã¡', 'ñ' en 'Ã±', etc. Construye un mapa de sustitución
    y aplícalo a cada documento.

    Estructura esperada:
        {"technique": "fix_encoding", "docs_modified",
         "ground_truth_broken_encoding", "examples": [{id, before, after}]}

    Pistas:
      - Mapa: {"Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
               "Ã±": "ñ", "Ã¼": "ü", "Â¿": "¿", "Â¡": "¡"}.
      - Cuenta cuántos docs cambian tras aplicar el fix.
      - El ground truth está en d["_noise"] (lista con 'broken_encoding').
    """
    return _exercise_placeholder("CLEAN-1", "Repara mojibake con un mapa de sustitución Ã¡→á, etc.")


@router.get("/strip_html")
async def strip_html_endpoint() -> dict:
    """
    EJERCICIO CLEAN-2 — Elimina HTML residual + boilerplate.

    Quita:
      - <ref>...</ref> y <ref/>
      - {{cite ...}}, {{Ficha...}}
      - [[link|texto]] → texto, [[link]] → link
      - <!-- comentarios -->, <etiquetas>
      - Bloques boilerplate ("== Véase también ==", "== Referencias ==", etc.)
        desde el marcador hasta el final del doc.

    Pistas:
      - Usa re.sub con flags=re.DOTALL para los <ref> multilinea.
      - Para [[a|b]] conserva el grupo 2: re.sub(r"\\[\\[[^\\]|]+\\|([^\\]]+)\\]\\]", r"\\1", t).
      - Normaliza espacios al final (\\n{3,} → \\n\\n).
    """
    return _exercise_placeholder("CLEAN-2", "Elimina <ref>/{{cite}}/[[wikilinks]]/boilerplate con regex.")


@router.get("/length_filter")
async def length_filter_endpoint(
    min_chars: int = Query(200, ge=0),
    max_chars: int = Query(15000, ge=100),
) -> dict:
    """
    EJERCICIO CLEAN-3 — Descarta docs demasiado cortos o largos.

    Cuenta los que caen fuera de [min_chars, max_chars] y reporta cuántos
    se conservan. Valida contra ground truth 'too_short' y 'too_long'.

    Pistas:
      - len(d["text"]) < min_chars → too short.
      - len(d["text"]) > max_chars → too long.
    """
    return _exercise_placeholder("CLEAN-3", "Filtra docs por longitud [min_chars, max_chars].")


@router.get("/language_filter")
async def language_filter_endpoint(target_lang: str = Query("es")) -> dict:
    """
    EJERCICIO CLEAN-4 — Detecta idioma y descarta no-español.

    Implementa una heurística simple: cuenta stopwords en español vs inglés
    en cada doc. Si gana inglés, el doc no es español.

    Pistas:
      - ES stopwords: el, la, los, de, que, en, y, a, con, por, para, ...
      - EN stopwords: the, of, and, to, in, is, that, for, with, this, ...
      - words = re.findall(r"\\b\\w+\\b", text.lower()).
      - Devuelve precision/recall contra ground truth 'wrong_lang'.
    """
    return _exercise_placeholder("CLEAN-4", "Detecta idioma por stopwords ES vs EN. Descarta los no-target.")


@router.get("/pii_removal")
async def pii_removal_endpoint() -> dict:
    """
    EJERCICIO CLEAN-5 — Tacha emails y teléfonos.

    Sustituye emails por [EMAIL] y teléfonos por [TELEFONO].

    Pistas:
      - Email: r"\\b[\\w.+-]+@[\\w-]+\\.[\\w.-]+\\b".
      - Teléfono: r"\\+?\\d[\\d\\s]{7,}\\d".
      - Cuenta cuántas redacciones haces en total.
    """
    return _exercise_placeholder("CLEAN-5", "Tacha emails ([EMAIL]) y teléfonos ([TELEFONO]) con regex.")


@router.get("/pipeline")
async def pipeline_endpoint(
    min_chars: int = Query(200),
    max_chars: int = Query(15000),
    target_lang: str = Query("es"),
) -> dict:
    """
    EJERCICIO CLEAN-6 — Aplica las 5 técnicas en orden.

    Orden recomendado: encoding → html → pii → length → language.
    Reporta docs y chars antes/después + porcentajes de reducción.

    Pistas:
      - Reutiliza las funciones de CLEAN-1..5.
      - El orden importa: arregla encoding ANTES de detectar idioma.
      - El corpus resultante alimenta el bloque dedup.
    """
    return _exercise_placeholder("CLEAN-6", "Aplica las 5 técnicas en orden y mide la reducción total.")
