"""Bloque TOKENIZE — scaffolds (versión alumno).

Cuatro ejercicios sobre tokenización BPE:

  TOK-1  train        entrena BPE (merges + vocabulario)
  TOK-2  encode       tokeniza un texto
  TOK-3  vocab_stats  estadísticas + compresión
  TOK-4  build_shards corpus → train.bin / val.bin (nanoGPT)

El tokenizer BPE base ya está implementado en src/tokenize/bpe.py — tu
trabajo es conectar los endpoints (entrenar, cachear, codificar, generar
los shards).

Flujo:
  1. Implementa las funciones aquí (usa BPETokenizer de src.tokenize.bpe).
  2. ./lab.sh llmprep restart
  3. Recarga la pestaña Tokenize.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/llmprep/tokenize", tags=["llmprep-tokenize"])


def _ph(exercise: str, hint: str) -> dict:
    return {"error": "scaffold", "exercise": exercise, "hint": hint, "available": False}


@router.get("/train")
async def train(
    num_merges: int = Query(500, ge=50, le=2000),
    sample: int = Query(2000, ge=200, le=5500),
) -> dict:
    """
    EJERCICIO TOK-1 — Entrena el tokenizer BPE.

    Usa BPETokenizer de src.tokenize.bpe. Entrénalo sobre los textos del
    corpus y CACHÉALO en una variable de módulo para que los otros
    endpoints lo reutilicen.

    Pistas:
      - tok = BPETokenizer(); stats = tok.train(texts, num_merges).
      - Guarda tok en una global _tokenizer.
      - Devuelve stats (vocab_size, num_merges, first_merges).
    """
    return _ph("TOK-1", "Entrena BPETokenizer y cachéalo en _tokenizer global.")


@router.get("/encode")
async def encode(text: str = Query("la fotosíntesis es un proceso biológico fundamental")) -> dict:
    """
    EJERCICIO TOK-2 — Tokeniza un texto.

    Devuelve tokens, ids, texto decodificado y ratio de compresión
    (chars/token).

    Pistas:
      - _tokenizer.encode_tokens(text) y _tokenizer.encode(text).
      - compression = len(text) / len(ids).
    """
    return _ph("TOK-2", "Codifica el texto con el tokenizer entrenado (encode + encode_tokens).")


@router.get("/vocab_stats")
async def vocab_stats(sample: int = Query(1000, ge=100, le=5500)) -> dict:
    """
    EJERCICIO TOK-3 — Estadísticas del vocabulario.

    Recorre el corpus, cuenta chars y tokens, calcula el ratio de
    compresión y los tokens más frecuentes.

    Pistas:
      - Counter sobre encode_tokens de cada doc.
      - compression_ratio = total_chars / total_tokens.
    """
    return _ph("TOK-3", "Calcula vocab_size, compresión y tokens más frecuentes.")


@router.post("/build_shards")
async def build_shards(
    sample: int = Query(3000, ge=200, le=5500),
    val_fraction: float = Query(0.1, ge=0.01, le=0.3),
) -> dict:
    """
    EJERCICIO TOK-4 — Genera los shards binarios estilo nanoGPT.

    Codifica todo el corpus a una secuencia de ids, sepárala en train/val
    y guárdala como uint16 en gold/train.bin y gold/val.bin. Guarda
    también el vocabulario en gold/vocab.json.

    Pistas:
      - np.array(all_ids, dtype=np.uint16).tofile(path).
      - val = arr[:n_val], train = arr[n_val:].
      - Estos shards alimentan el bloque train.
    """
    return _ph("TOK-4", "Codifica el corpus a train.bin/val.bin (uint16) + vocab.json.")
