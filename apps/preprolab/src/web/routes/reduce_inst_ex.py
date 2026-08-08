"""Bloque REDUCE_INST — scaffolds (versión alumno).

Cinco ejercicios sobre instance selection del Tema 5:

  INST-1  srswor          Aleatorio sin reemplazo
  INST-2  stratified      Preserva proporción de clases
  INST-3  balanced        Under/oversampling
  INST-4  by_clusters     K-Means + selecciona clusters completos
  INST-5  kmeans_compress Reduce N a K centroides

Flujo:
  1. Implementa las funciones aquí.
  2. ./lab.sh preprolab restart
  3. Recarga la pestaña Reducción inst.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/reduce_inst", tags=["preprolab-reduce_inst"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


@router.get("/srswor/{tabla}")
async def srswor(
    tabla: str,
    target: str = Query("failure_next_48h"),
    fraction: float = Query(0.3, gt=0.0, le=1.0),
    seed: int = Query(42),
) -> dict:
    """
    EJERCICIO INST-1 — SRSWOR (muestreo aleatorio simple sin reemplazo).

    Cada fila probabilidad uniforme 1/N. Rápido, pierde subgrupos
    minoritarios.

    Estructura esperada:
        {
          "table", "target", "method", "fraction",
          "rows_before", "rows_after",
          "class_distribution_before": {clase: count},
          "class_distribution_after": {clase: count},
          "ratio_preserved": float  # mean(target_after) / mean(target_before)
        }

    Pistas:
      - df.sample(n=N, replace=False, random_state=seed).
    """
    return _exercise_placeholder(
        "INST-1",
        "Implementa muestreo aleatorio simple sin reemplazo (df.sample).",
    )


@router.get("/stratified/{tabla}")
async def stratified(
    tabla: str,
    target: str = Query("failure_next_48h"),
    fraction: float = Query(0.3, gt=0.0, le=1.0),
    seed: int = Query(42),
) -> dict:
    """
    EJERCICIO INST-2 — Stratified Sampling.

    Para cada clase, muestrea `fraction` de sus filas. Preserva la
    proporción original.

    Pistas:
      - df.groupby(target).apply(lambda g: g.sample(frac=fraction, ...)).
      - Usa include_groups=True (pandas reciente).
    """
    return _exercise_placeholder(
        "INST-2",
        "Implementa stratified sampling con groupby + sample(frac).",
    )


@router.get("/balanced/{tabla}")
async def balanced(
    tabla: str,
    target: str = Query("failure_next_48h"),
    strategy: str = Query("undersample", regex="^(undersample|oversample)$"),
    seed: int = Query(42),
) -> dict:
    """
    EJERCICIO INST-3 — Distribución equitativa entre clases.

      undersample: reduce mayoritaria al tamaño de la minoritaria.
      oversample:  duplica minoritaria (replace=True) al tamaño de la
                   mayoritaria.

    Pistas:
      - sizes = df.groupby(target).size().
      - target_size = sizes.min() o sizes.max() según strategy.
      - replace=True solo para oversample.
    """
    return _exercise_placeholder(
        "INST-3",
        "Implementa under/oversampling para forzar balance de clases.",
    )


@router.get("/by_clusters/{tabla}")
async def by_clusters(
    tabla: str,
    target: str = Query("failure_next_48h"),
    n_clusters: int = Query(10, ge=2, le=50),
    n_clusters_to_select: int = Query(3, ge=1),
    seed: int = Query(42),
) -> dict:
    """
    EJERCICIO INST-4 — Selection por clusters.

    K-Means(n_clusters) → seleccionar `n_clusters_to_select` clusters
    completos (los más grandes para preservar masa).

    Pistas:
      - StandardScaler + KMeans con random_state=seed.
      - sizes = pd.Series(labels).value_counts().
      - chosen = sizes.head(n_clusters_to_select).index.
    """
    return _exercise_placeholder(
        "INST-4",
        "Implementa K-Means + selección de clusters completos por tamaño.",
    )


@router.get("/kmeans_compress/{tabla}")
async def kmeans_compress(
    tabla: str,
    target: str = Query("failure_next_48h"),
    k: int = Query(50, ge=5, le=500),
    seed: int = Query(42),
) -> dict:
    """
    EJERCICIO INST-5 — Cuantización vectorial con K-Means.

    Reduce N filas a K prototipos (centroides). Cada centroide hereda
    el label modal de las filas que agrupa.

    Pistas:
      - K-Means.cluster_centers_ en escala estandarizada.
      - scaler.inverse_transform() para volver a escala original.
      - df.groupby('_cluster')[target].agg(lambda s: s.mode().iloc[0]).
      - compression_ratio = N / k.
    """
    return _exercise_placeholder(
        "INST-5",
        "Implementa compresión K-Means: N filas → K centroides con label modal.",
    )
