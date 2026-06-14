"""Bloque DEDUP — soluciones.

Detección de duplicados y near-duplicates en el corpus, con carga del
grafo de similitud a Neo4j (la pata poliglota de LLM Lab).

  DEDUP-1  exact            duplicados exactos por hash del texto
  DEDUP-2  minhash          firmas MinHash por documento (estima Jaccard)
  DEDUP-3  lsh_candidates   LSH banding → pares candidatos near-dup
  DEDUP-4  build_graph      carga :Document -[:SIMILAR_TO {jaccard}]-> en Neo4j
  DEDUP-5  graph_clusters   consulta Cypher: clusters de near-duplicates

MinHash y LSH implementados desde cero (sin datasketch) para que el
laboratorio sea self-contained y el alumno vea la mecánica.

La idea pedagógica: los content farms y las páginas espejo crean
near-duplicates que inflan el corpus y sesgan el modelo. Detectarlos y
explorarlos como grafo (con Cypher) conecta con lo aprendido en SocialLab.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from src.web.corpus_loader import load_corpus

router = APIRouter(prefix="/api/llmprep/dedup", tags=["llmprep-dedup"])

# Parámetros MinHash/LSH
NUM_HASHES = 64
NUM_BANDS = 16   # → rows_per_band = 4
SHINGLE_K = 3    # word-level shingles de 3 palabras
_MERSENNE = (1 << 31) - 1  # primo para hashing

# Coeficientes de las funciones hash (deterministas)
_rng = np.random.default_rng(7)
_A = _rng.integers(1, _MERSENNE, size=NUM_HASHES, dtype=np.int64)
_B = _rng.integers(0, _MERSENNE, size=NUM_HASHES, dtype=np.int64)


def _shingles(text: str, k: int = SHINGLE_K) -> set[int]:
    """Convierte texto en conjunto de hashes de k-shingles (nivel palabra)."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < k:
        return {hash(" ".join(words)) & 0xFFFFFFFF} if words else set()
    sh = set()
    for i in range(len(words) - k + 1):
        gram = " ".join(words[i:i + k])
        h = int(hashlib.md5(gram.encode()).hexdigest()[:8], 16)
        sh.add(h)
    return sh


def _minhash_signature(shingles: set[int]) -> np.ndarray:
    """Firma MinHash: para cada función hash, el mínimo sobre los shingles."""
    if not shingles:
        return np.full(NUM_HASHES, _MERSENNE, dtype=np.int64)
    arr = np.array(list(shingles), dtype=np.int64)
    # (a * x + b) mod p para cada función → matriz (NUM_HASHES, n_shingles)
    hashed = (np.outer(_A, arr) + _B[:, None]) % _MERSENNE
    return hashed.min(axis=1)


def _exact_hash(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()


# ============================================================
# DEDUP-1: duplicados exactos
# ============================================================


@router.get("/exact")
async def exact() -> dict:
    """DEDUP-1 — Detecta duplicados exactos por hash del texto normalizado."""
    docs = load_corpus()
    seen: dict[str, str] = {}
    duplicates = []
    for d in docs:
        h = _exact_hash(d.get("text", ""))
        if h in seen:
            duplicates.append({"id": d["id"], "duplicate_of": seen[h]})
        else:
            seen[h] = d["id"]
    truth = sum(1 for d in docs if "exact_dup" in d.get("_noise", []))
    return {
        "technique": "exact_dedup",
        "n_docs": len(docs),
        "unique_texts": len(seen),
        "exact_duplicates_found": len(duplicates),
        "ground_truth_exact_dup": truth,
        "examples": duplicates[:10],
    }


# ============================================================
# DEDUP-2: firmas MinHash
# ============================================================


@router.get("/minhash")
async def minhash(sample: int = Query(500, ge=50, le=2000)) -> dict:
    """DEDUP-2 — Calcula firmas MinHash y estima Jaccard en una muestra de pares."""
    docs = load_corpus()[:sample]
    sigs = [_minhash_signature(_shingles(d.get("text", ""))) for d in docs]

    # Estima Jaccard de algunos pares conocidos vs aleatorios
    examples = []
    n = len(sigs)
    # Buscar pares con alta similitud
    pairs_checked = 0
    for i in range(n):
        for j in range(i + 1, min(i + 30, n)):
            est = float(np.mean(sigs[i] == sigs[j]))
            if est > 0.5:
                examples.append({
                    "doc_a": docs[i]["id"], "doc_b": docs[j]["id"],
                    "estimated_jaccard": round(est, 3),
                    "a_is_near_dup": "near_dup" in docs[i].get("_noise", []),
                    "b_is_near_dup": "near_dup" in docs[j].get("_noise", []),
                })
            pairs_checked += 1
            if len(examples) >= 10:
                break
        if len(examples) >= 10:
            break
    return {
        "technique": "minhash_signatures",
        "num_hashes": NUM_HASHES,
        "shingle_k": SHINGLE_K,
        "sample_size": len(docs),
        "pairs_checked": pairs_checked,
        "high_similarity_pairs": examples,
    }


# ============================================================
# DEDUP-3: LSH candidates
# ============================================================


def _lsh_candidate_pairs(sigs: list[np.ndarray]) -> set[tuple[int, int]]:
    """LSH banding: divide la firma en bandas, agrupa por bucket de banda."""
    rows = NUM_HASHES // NUM_BANDS
    candidates: set[tuple[int, int]] = set()
    for band in range(NUM_BANDS):
        buckets: dict[bytes, list[int]] = {}
        start = band * rows
        for idx, sig in enumerate(sigs):
            key = sig[start:start + rows].tobytes()
            buckets.setdefault(key, []).append(idx)
        for bucket in buckets.values():
            if len(bucket) > 1:
                for a in range(len(bucket)):
                    for b in range(a + 1, len(bucket)):
                        candidates.add((bucket[a], bucket[b]))
    return candidates


@router.get("/lsh_candidates")
async def lsh_candidates(
    sample: int = Query(1500, ge=100, le=5500),
    threshold: float = Query(0.5, ge=0.1, le=1.0),
) -> dict:
    """DEDUP-3 — LSH banding para encontrar pares candidatos a near-duplicate."""
    docs = load_corpus()[:sample]
    sigs = [_minhash_signature(_shingles(d.get("text", ""))) for d in docs]
    candidates = _lsh_candidate_pairs(sigs)

    # Verificar candidatos con Jaccard estimado y filtrar por threshold
    confirmed = []
    for i, j in candidates:
        est = float(np.mean(sigs[i] == sigs[j]))
        if est >= threshold:
            confirmed.append({
                "doc_a": docs[i]["id"], "doc_b": docs[j]["id"],
                "jaccard": round(est, 3),
            })
    confirmed.sort(key=lambda x: x["jaccard"], reverse=True)

    # Cuántos de los confirmados involucran un near_dup real
    near_dup_ids = {d["id"] for d in docs if "near_dup" in d.get("_noise", []) or "exact_dup" in d.get("_noise", [])}
    involving_truth = sum(
        1 for c in confirmed if c["doc_a"] in near_dup_ids or c["doc_b"] in near_dup_ids
    )
    return {
        "technique": "lsh_banding",
        "num_bands": NUM_BANDS,
        "rows_per_band": NUM_HASHES // NUM_BANDS,
        "sample_size": len(docs),
        "threshold": threshold,
        "candidate_pairs": len(candidates),
        "confirmed_pairs": len(confirmed),
        "pairs_involving_known_dup": involving_truth,
        "top_pairs": confirmed[:15],
    }


# ============================================================
# DEDUP-4: build graph en Neo4j
# ============================================================


@router.post("/build_graph")
async def build_graph(
    sample: int = Query(1500, ge=100, le=5500),
    threshold: float = Query(0.5, ge=0.3, le=1.0),
) -> dict:
    """DEDUP-4 — Carga el grafo de similitud a Neo4j.

    Crea nodos :Document y aristas :SIMILAR_TO con peso = jaccard estimado.
    El alumno luego explora los clusters con Cypher (DEDUP-5).
    """
    from infra.shared.neo4j import neo4j_write
    from infra.shared.config_base import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

    docs = load_corpus()[:sample]
    sigs = [_minhash_signature(_shingles(d.get("text", ""))) for d in docs]
    candidates = _lsh_candidate_pairs(sigs)

    edges = []
    for i, j in candidates:
        est = float(np.mean(sigs[i] == sigs[j]))
        if est >= threshold:
            edges.append((docs[i]["id"], docs[j]["id"], round(est, 3),
                          docs[i].get("title", ""), docs[j].get("title", "")))

    # Limpiar grafo previo + cargar
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("MATCH (d:Document) DETACH DELETE d")
            # Cargar en lotes
            for a, b, jac, ta, tb in edges:
                session.run(
                    """
                    MERGE (x:Document {id: $a}) ON CREATE SET x.title = $ta
                    MERGE (y:Document {id: $b}) ON CREATE SET y.title = $tb
                    MERGE (x)-[r:SIMILAR_TO]->(y) SET r.jaccard = $jac
                    """,
                    a=a, b=b, jac=jac, ta=ta, tb=tb,
                )
        driver.close()
        loaded = True
    except Exception as e:
        return {"technique": "build_graph", "error": f"Neo4j no disponible: {e}", "edges_computed": len(edges)}

    return {
        "technique": "build_graph",
        "neo4j_loaded": loaded,
        "documents_in_graph": len({e[0] for e in edges} | {e[1] for e in edges}),
        "similar_to_edges": len(edges),
        "threshold": threshold,
        "note": "Explora el grafo con DEDUP-5 (graph_clusters) o en el Neo4j browser (:7474).",
    }


# ============================================================
# DEDUP-5: clusters vía Cypher
# ============================================================


@router.get("/graph_clusters")
async def graph_clusters(limit: int = Query(10, ge=1, le=50)) -> dict:
    """DEDUP-5 — Consulta Cypher: documentos con más vecinos near-dup.

    Devuelve los documentos con mayor grado en el grafo SIMILAR_TO
    (los que tienen más casi-duplicados → candidatos a content farm).
    """
    from infra.shared.config_base import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # Grado de cada documento
            result = session.run(
                """
                MATCH (d:Document)-[r:SIMILAR_TO]-(other:Document)
                WITH d, count(DISTINCT other) AS neighbors, avg(r.jaccard) AS avg_jac
                RETURN d.id AS id, d.title AS title, neighbors, avg_jac
                ORDER BY neighbors DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            clusters = [
                {"id": r["id"], "title": r["title"],
                 "neighbors": r["neighbors"], "avg_jaccard": round(r["avg_jac"], 3)}
                for r in result
            ]
            # Total de nodos/aristas
            stats = session.run(
                "MATCH (d:Document) WITH count(d) AS nodes "
                "MATCH ()-[r:SIMILAR_TO]->() RETURN nodes, count(r) AS edges"
            ).single()
            graph_stats = {"nodes": stats["nodes"], "edges": stats["edges"]} if stats else {"nodes": 0, "edges": 0}
        driver.close()
    except Exception as e:
        raise HTTPException(503, detail=f"Neo4j no disponible o grafo vacío: {e}. Ejecuta build_graph primero.")

    return {
        "technique": "graph_clusters",
        "graph_stats": graph_stats,
        "top_documents_by_neighbors": clusters,
        "note": "Documentos con muchos vecinos SIMILAR_TO son candidatos a content farm / scraping masivo.",
    }
