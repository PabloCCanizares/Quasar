"""Bloque TRAIN — scaffolds (versión alumno).

Tres ejercicios sobre entrenamiento de un modelo de lenguaje:

  TRAIN-1  train     entrena el modelo, reporta perplexity
  TRAIN-2  generate  muestrea texto del modelo
  TRAIN-3  compare   LA DEMO: sucio vs limpio

El modelo n-gram base ya está en src/train/ngram_lm.py — tu trabajo es
conectar los endpoints (entrenar, cachear, generar, comparar).

Flujo:
  1. Implementa las funciones aquí (usa NgramLM de src.train.ngram_lm).
  2. ./lab.sh llmprep restart
  3. Recarga la pestaña Train.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/llmprep/train", tags=["llmprep-train"])


def _ph(exercise: str, hint: str) -> dict:
    return {"error": "scaffold", "exercise": exercise, "hint": hint, "available": False}


@router.get("/train")
async def train_endpoint(
    n: int = Query(3, ge=2, le=4),
    sample: int = Query(3000, ge=200, le=5500),
) -> dict:
    """
    EJERCICIO TRAIN-1 — Entrena el modelo de lenguaje sobre el corpus limpio.

    Limpia los textos (reutiliza las funciones del bloque clean), entrena
    un NgramLM, calcula la perplexity sobre validación y CACHÉA el modelo.

    Pistas:
      - from src.train.ngram_lm import NgramLM.
      - Limpia: fix_encoding → strip_html → redact_pii (de routes.clean).
      - model.train(train_texts); model.perplexity(val_texts).
      - Guarda el modelo en una global _model.

    Compruebalo:
      - La perplejidad tiene que bajar segun avanza el entrenamiento. Si sube
        o se queda plana, algo va mal en la actualizacion.
      - La perplejidad nunca puede ser menor que 1.
      - Entrenar sobre mas datos deberia mejorarla; si no cambia nada,
        comprueba que estas leyendo el corpus entero.
    """
    return _ph("TRAIN-1", "Entrena NgramLM sobre corpus limpio, calcula perplexity, cachéalo.")


@router.get("/generate")
async def generate_endpoint(
    prompt: str = Query("la"),
    max_tokens: int = Query(40, ge=5, le=150),
    temperature: float = Query(0.8, ge=0.1, le=2.0),
) -> dict:
    """
    EJERCICIO TRAIN-2 — Genera texto muestreando del modelo.

    Pistas:
      - _model.generate(prompt, max_tokens, temperature).
      - Temperature baja = más conservador; alta = más aleatorio.

    Compruebalo:
      - El texto generado tiene que usar solo tokens del vocabulario.
      - Con temperatura baja el texto se repite mucho; con temperatura alta
        se vuelve incoherente. Si no notas diferencia al cambiarla, el
        muestreo no la esta usando.
      - Generar dos veces con la misma semilla tiene que dar lo mismo.
    """
    return _ph("TRAIN-2", "Genera texto con _model.generate(prompt, max_tokens, temperature).")


@router.get("/compare")
async def compare_endpoint(
    n: int = Query(3, ge=2, le=4),
    sample: int = Query(3000, ge=200, le=5500),
    prompt: str = Query("la"),
) -> dict:
    """
    EJERCICIO TRAIN-3 — LA DEMO: modelo sucio vs limpio.

    Entrena DOS modelos idénticos:
      - dirty: sobre el texto crudo (con HTML, mojibake, gibberish).
      - clean: sobre el texto limpio.
    Evalúa ambos sobre el MISMO conjunto de validación limpio (referencia
    justa). Compara perplexity y muestra una generación de cada uno.

    Conclusión esperada: el modelo limpio tiene menor perplexity y genera
    español coherente; el sucio genera basura (HTML/mojibake).

    Pistas:
      - dirty_model.train(textos_crudos), clean_model.train(textos_limpios).
      - Ambos se evalúan sobre val_texts LIMPIOS.
      - perplexity_improvement = (dirty_ppl - clean_ppl) / dirty_ppl.

    Compruebalo:
      - Esta es la demo: la perplejidad del modelo entrenado con el corpus
        limpio tiene que ser MENOR que la del sucio, evaluando ambos sobre el
        mismo conjunto.
      - Si te sale al reves o casi igual, lo mas probable es que estes
        evaluando cada modelo sobre su propio conjunto: entonces no son
        comparables. Los dos tienen que medirse contra el mismo texto.
      - Mira tambien el tamano del vocabulario: el corpus sucio genera mas
        tokens distintos por culpa de la basura, y eso es parte de por que
        aprende peor.
    """
    return _ph("TRAIN-3", "Entrena 2 modelos (sucio/limpio), compara perplexity + generación.")
