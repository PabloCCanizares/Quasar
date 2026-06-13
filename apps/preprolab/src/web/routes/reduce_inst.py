"""Bloque REDUCE_INST — soluciones.

Implementa la reducción del eje filas (instance selection) del Tema 5:

  INST-1  srswor          Simple Random Sampling Without Replacement
  INST-2  stratified      Preserva proporción de cada clase
  INST-3  balanced        Fuerza distribución equitativa (under/oversampling)
  INST-4  by_clusters     K-Means primero, selecciona clusters completos
  INST-5  kmeans_compress Reduce N filas a K centroides (cuantización vectorial)

Todos los métodos trabajan sobre la tabla `robots` con target
`failure_next_48h` (necesario para estratificado y balanceado).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/reduce_inst", tags=["preprolab-reduce_inst"])


# ============================================================
# Helpers
# ============================================================

def _prepare(tabla: str, target: str) -> tuple[pd.DataFrame, list[str]]:
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if target not in df.columns:
        raise HTTPException(400, detail=f"Target {target} no existe")
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and c != target
    ]
    sub = df[numeric_cols + [target]].dropna().reset_index(drop=True)
    if len(sub) < 50:
        raise HTTPException(400, detail="Necesitamos al menos 50 filas completas")
    return sub, numeric_cols


def _class_distribution(y: np.ndarray) -> dict:
    vals, counts = np.unique(y, return_counts=True)
    return {str(int(v)): int(c) for v, c in zip(vals, counts)}


# ============================================================
# INST-1: SRSWOR
# ============================================================


@router.get("/srswor/{tabla}")
async def srswor(
    tabla: str,
    target: str = Query("failure_next_48h"),
    fraction: float = Query(0.3, gt=0.0, le=1.0),
    seed: int = Query(42),
) -> dict:
    """
    INST-1 — Simple Random Sampling Without Replacement.

    Cada fila tiene probabilidad uniforme 1/N de ser seleccionada.
    Rápido pero puede perder subgrupos minoritarios.
    """
    df, cols = _prepare(tabla, target)
    n = int(len(df) * fraction)
    sampled = df.sample(n=n, replace=False, random_state=seed)

    return {
        "table": tabla,
        "target": target,
        "method": "srswor",
        "fraction": fraction,
        "rows_before": int(len(df)),
        "rows_after": int(len(sampled)),
        "class_distribution_before": _class_distribution(df[target].values),
        "class_distribution_after": _class_distribution(sampled[target].values),
        "ratio_preserved": round(
            sampled[target].mean() / max(0.001, df[target].mean()), 3
        ),
    }


# ============================================================
# INST-2: Stratified
# ============================================================


@router.get("/stratified/{tabla}")
async def stratified(
    tabla: str,
    target: str = Query("failure_next_48h"),
    fraction: float = Query(0.3, gt=0.0, le=1.0),
    seed: int = Query(42),
) -> dict:
    """
    INST-2 — Stratified Sampling.

    Para cada clase, muestrea `fraction` de sus filas. Preserva la
    proporción original. Ideal para clasificación con clases minoritarias.
    """
    df, cols = _prepare(tabla, target)
    sampled = (
        df.groupby(target, group_keys=False)
        .apply(lambda g: g.sample(frac=fraction, random_state=seed), include_groups=True)
        .reset_index(drop=True)
    )

    return {
        "table": tabla,
        "target": target,
        "method": "stratified",
        "fraction": fraction,
        "rows_before": int(len(df)),
        "rows_after": int(len(sampled)),
        "class_distribution_before": _class_distribution(df[target].values),
        "class_distribution_after": _class_distribution(sampled[target].values),
        "ratio_preserved": round(
            sampled[target].mean() / max(0.001, df[target].mean()), 3
        ),
    }


# ============================================================
# INST-3: Balanced (under/oversampling)
# ============================================================


@router.get("/balanced/{tabla}")
async def balanced(
    tabla: str,
    target: str = Query("failure_next_48h"),
    strategy: str = Query("undersample", regex="^(undersample|oversample)$"),
    seed: int = Query(42),
) -> dict:
    """
    INST-3 — Forzar distribución equitativa entre clases.

      undersample: muestrea de la clase mayoritaria al tamaño de la
                   minoritaria. Pierde datos pero mantiene calidad.
      oversample:  muestrea con reemplazo de la minoritaria al tamaño
                   de la mayoritaria. Mantiene tamaño pero duplica.
    """
    df, cols = _prepare(tabla, target)
    classes = df.groupby(target)
    sizes = classes.size()
    min_size = int(sizes.min())
    max_size = int(sizes.max())
    target_size = min_size if strategy == "undersample" else max_size

    parts = []
    for cls, group in classes:
        if len(group) >= target_size and strategy == "undersample":
            parts.append(group.sample(n=target_size, replace=False, random_state=seed))
        elif len(group) < target_size and strategy == "oversample":
            parts.append(group.sample(n=target_size, replace=True, random_state=seed))
        else:
            parts.append(group)

    sampled = pd.concat(parts).reset_index(drop=True)

    return {
        "table": tabla,
        "target": target,
        "method": "balanced",
        "strategy": strategy,
        "target_size_per_class": target_size,
        "rows_before": int(len(df)),
        "rows_after": int(len(sampled)),
        "class_distribution_before": _class_distribution(df[target].values),
        "class_distribution_after": _class_distribution(sampled[target].values),
    }


# ============================================================
# INST-4: By clusters
# ============================================================


@router.get("/by_clusters/{tabla}")
async def by_clusters(
    tabla: str,
    target: str = Query("failure_next_48h"),
    n_clusters: int = Query(10, ge=2, le=50),
    n_clusters_to_select: int = Query(3, ge=1),
    seed: int = Query(42),
) -> dict:
    """
    INST-4 — Selection por clusters.

    Aplica K-Means para agrupar las instancias en K clusters y selecciona
    `n_clusters_to_select` clusters completos. Útil en datos espaciales
    o temporales donde los clusters son coherentes.
    """
    if n_clusters_to_select > n_clusters:
        raise HTTPException(400, detail="n_clusters_to_select debe ser ≤ n_clusters")

    df, cols = _prepare(tabla, target)

    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    X_scaled = StandardScaler().fit_transform(df[cols])
    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    labels = km.fit_predict(X_scaled)
    df = df.assign(_cluster=labels)

    # Distribución de clusters (por tamaño)
    cluster_sizes = pd.Series(labels).value_counts().sort_values(ascending=False)

    # Seleccionar los n_clusters_to_select clusters más representativos
    # (los más grandes, para no perder masa de datos)
    chosen = cluster_sizes.head(n_clusters_to_select).index.tolist()
    sampled = df[df["_cluster"].isin(chosen)].drop(columns=["_cluster"]).reset_index(drop=True)

    return {
        "table": tabla,
        "target": target,
        "method": "by_clusters",
        "n_clusters": n_clusters,
        "n_clusters_to_select": n_clusters_to_select,
        "chosen_clusters": [int(c) for c in chosen],
        "rows_before": int(len(df)),
        "rows_after": int(len(sampled)),
        "class_distribution_before": _class_distribution(df[target].values),
        "class_distribution_after": _class_distribution(sampled[target].values),
        "cluster_sizes_top10": {str(int(k)): int(v) for k, v in cluster_sizes.head(10).items()},
    }


# ============================================================
# INST-5: K-Means compression (vector quantization)
# ============================================================


@router.get("/kmeans_compress/{tabla}")
async def kmeans_compress(
    tabla: str,
    target: str = Query("failure_next_48h"),
    k: int = Query(50, ge=5, le=500),
    seed: int = Query(42),
) -> dict:
    """
    INST-5 — Compresión vectorial con K-Means.

    Reduce N filas a K prototipos (centroides). Cada centroide hereda
    el label modal de las filas que agrupa. Ideal para pre-procesar
    datasets enormes antes de algoritmos O(n²) como KNN o SVM.
    """
    df, cols = _prepare(tabla, target)

    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[cols])
    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = km.fit_predict(X_scaled)

    # Centroides desestandarizados
    centroids_orig = scaler.inverse_transform(km.cluster_centers_)
    centroid_df = pd.DataFrame(centroids_orig, columns=cols)

    # Label modal por centroide
    df_temp = df.assign(_cluster=labels)
    mode_per_cluster = (
        df_temp.groupby("_cluster")[target]
        .agg(lambda s: int(s.mode().iloc[0]))
    )
    centroid_df[target] = [mode_per_cluster.get(i, 0) for i in range(k)]

    # Tamaños de cluster
    cluster_sizes = pd.Series(labels).value_counts()

    return {
        "table": tabla,
        "target": target,
        "method": "kmeans_compress",
        "k": k,
        "rows_before": int(len(df)),
        "rows_after": int(len(centroid_df)),
        "compression_ratio": round(len(df) / len(centroid_df), 1),
        "class_distribution_before": _class_distribution(df[target].values),
        "class_distribution_after": _class_distribution(centroid_df[target].values),
        "cluster_size_stats": {
            "min": int(cluster_sizes.min()),
            "max": int(cluster_sizes.max()),
            "mean": round(float(cluster_sizes.mean()), 1),
            "median": int(cluster_sizes.median()),
        },
        "centroid_sample": centroid_df.head(5).to_dict("records"),
    }
