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

    Compruebalo:
      - El vocabulario final tiene que ser el tamano base mas el numero de
        fusiones que pediste, aproximadamente.
      - Las primeras fusiones deberian ser pares de caracteres muy comunes en
        espanol ('es', 'de', 'qu'). Si salen combinaciones raras, el conteo
        de frecuencias no esta bien.
      - Entrenar dos veces sobre el mismo corpus tiene que dar el mismo
        vocabulario: el algoritmo es determinista.
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

    Compruebalo:
      - Decodificar lo que acabas de codificar tiene que devolver el texto
        original, exactamente. Es la prueba definitiva y la mas facil de
        hacer.
      - El numero de tokens siempre es menor o igual que el de caracteres.
      - Un texto con palabras muy frecuentes usa menos tokens por caracter
        que uno con palabras raras. Si la proporcion es siempre la misma,
        las fusiones no se estan aplicando.
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

    Compruebalo:
      - La compresion (caracteres por token) tiene que ser mayor que 1. Si
        sale 1, estas tokenizando caracter a caracter.
      - Mas fusiones dan mejor compresion, con rendimientos decrecientes.
      - Compara el vocabulario del corpus sucio con el del limpio: el sucio
        deberia traer tokens basura (restos de HTML, referencias) que en el
        limpio no aparecen. Es la mejor senal de que la limpieza sirvio.
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

    Compruebalo:
      - Los dos shards juntos tienen que sumar el total de tokens del corpus.
      - La proporcion entre train y val tiene que ser la que pediste.
      - Los ficheros son binarios de enteros: su tamano en bytes tiene que
        cuadrar con el numero de tokens por el tamano del tipo. Si no cuadra,
        estas escribiendo con otro ancho del que crees.
    """
    return _ph("TOK-4", "Codifica el corpus a train.bin/val.bin (uint16) + vocab.json.")
