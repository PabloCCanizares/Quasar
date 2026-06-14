"""Bloque DEDUP — scaffolds (versión alumno).

Cinco ejercicios sobre deduplicación + grafo Neo4j:

  DEDUP-1  exact            duplicados exactos por hash
  DEDUP-2  minhash          firmas MinHash (estima Jaccard)
  DEDUP-3  lsh_candidates   LSH banding → pares near-dup
  DEDUP-4  build_graph      carga SIMILAR_TO a Neo4j (POST)
  DEDUP-5  graph_clusters   consulta Cypher de clusters

Flujo:
  1. Implementa las funciones aquí.
  2. ./lab.sh llmprep restart
  3. Recarga la pestaña Dedup.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/llmprep/dedup", tags=["llmprep-dedup"])


def _ph(exercise: str, hint: str) -> dict:
    return {"error": "scaffold", "exercise": exercise, "hint": hint, "available": False}


@router.get("/exact")
async def exact() -> dict:
    """
    EJERCICIO DEDUP-1 — Duplicados exactos por hash del texto normalizado.

    Hashea el texto (md5 del texto strip) de cada doc. Si dos docs comparten
    hash, son duplicados exactos.

    Estructura: {technique, n_docs, unique_texts, exact_duplicates_found,
                 ground_truth_exact_dup, examples}

    Pistas:
      - hashlib.md5(text.strip().encode()).hexdigest().
      - dict hash → primer id que lo tuvo.
    """
    return _ph("DEDUP-1", "Detecta duplicados exactos con md5 del texto.")


@router.get("/minhash")
async def minhash(sample: int = Query(500, ge=50, le=2000)) -> dict:
    """
    EJERCICIO DEDUP-2 — Firmas MinHash.

    Para cada doc: shingles (k-gramas de palabras) → hashea cada shingle →
    para cada una de N funciones hash, toma el MÍNIMO sobre los shingles.
    La fracción de valores MinHash iguales entre dos docs estima su Jaccard.

    Pistas:
      - Shingle k=3: " ".join(words[i:i+3]) para cada i.
      - N=64 funciones hash de la forma (a*x+b) mod p.
      - jaccard_estimado = mean(sig_a == sig_b).
    """
    return _ph("DEDUP-2", "Calcula firmas MinHash con shingles + N funciones hash min.")


@router.get("/lsh_candidates")
async def lsh_candidates(
    sample: int = Query(1500, ge=100, le=5500),
    threshold: float = Query(0.5, ge=0.1, le=1.0),
) -> dict:
    """
    EJERCICIO DEDUP-3 — LSH banding.

    Divide cada firma MinHash en B bandas de R filas. Dos docs que comparten
    el contenido EXACTO de alguna banda son candidatos a near-duplicate.
    Luego confirma con el Jaccard estimado >= threshold.

    Pistas:
      - rows_per_band = NUM_HASHES // NUM_BANDS.
      - bucket key = sig[start:start+rows].tobytes().
      - candidatos = pares en el mismo bucket de alguna banda.
    """
    return _ph("DEDUP-3", "Implementa LSH banding sobre las firmas MinHash.")


@router.post("/build_graph")
async def build_graph(
    sample: int = Query(1500, ge=100, le=5500),
    threshold: float = Query(0.5, ge=0.3, le=1.0),
) -> dict:
    """
    EJERCICIO DEDUP-4 — Carga el grafo de similitud a Neo4j.

    Crea nodos :Document y aristas :SIMILAR_TO {jaccard}. Limpia el grafo
    previo (MATCH (d:Document) DETACH DELETE d) antes de cargar.

    Pistas:
      - from infra.shared.config_base import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD.
      - MERGE (x:Document {id})... MERGE (x)-[r:SIMILAR_TO]->(y) SET r.jaccard.
      - Reutiliza el LSH de DEDUP-3 para obtener las aristas.
    """
    return _ph("DEDUP-4", "Carga :Document y :SIMILAR_TO {jaccard} a Neo4j.")


@router.get("/graph_clusters")
async def graph_clusters(limit: int = Query(10, ge=1, le=50)) -> dict:
    """
    EJERCICIO DEDUP-5 — Consulta Cypher de clusters.

    Devuelve los documentos con más vecinos SIMILAR_TO (candidatos a
    content farm).

    Cypher sugerido:
        MATCH (d:Document)-[r:SIMILAR_TO]-(other:Document)
        WITH d, count(DISTINCT other) AS neighbors, avg(r.jaccard) AS avg_jac
        RETURN d.id, d.title, neighbors, avg_jac
        ORDER BY neighbors DESC LIMIT $limit
    """
    return _ph("DEDUP-5", "Consulta Cypher: docs con más vecinos SIMILAR_TO.")
