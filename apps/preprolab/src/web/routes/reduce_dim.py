"""Bloque REDUCE_DIM — soluciones.

Implementa la reducción de dimensionalidad y feature selection del Tema 5.

Proyección (no lineal y lineal):
  REDDIM-1  pca         PCA con explained variance
  REDDIM-2  tsne        t-SNE 2D (visualización)

Feature selection (3 familias del PDF):
  REDDIM-3  filter      Chi², Pearson, varianza, mutual info
  REDDIM-4  wrapper     Forward Selection, Backward Elimination, RFE
  REDDIM-5  embedded    Lasso L1, RandomForest feature_importances_

Comparativa:
  REDDIM-6  compare     Aplica filter/wrapper/embedded sobre la misma
                        tabla y devuelve qué features prioriza cada uno

AutoEncoders quedan documentados en el README pero NO se implementan
aquí (requeriría PyTorch + entrenamiento costoso). Es un ejercicio
opcional para fases posteriores.

Notas:
  - Trabajamos solo sobre `robots` porque es la única tabla con target
    (`failure_next_48h`) necesario para los métodos supervisados.
  - Limitamos t-SNE a `max_rows` filas para que el endpoint responda
    en <30s (t-SNE es O(n²)).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/reduce_dim", tags=["preprolab-reduce_dim"])


# ============================================================
# Helpers
# ============================================================

def _prepare_xy(tabla: str, target: str) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Prepara X (numéricas, sin nulls) e y (target).

    Devuelve (X DataFrame con índice reindexado, y array, numeric_cols).
    """
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

    X = sub[numeric_cols]
    y = sub[target].astype(int).values
    return X, y, numeric_cols


# ============================================================
# REDDIM-1: PCA
# ============================================================


@router.get("/pca/{tabla}")
async def pca(
    tabla: str,
    target: str = Query("failure_next_48h"),
    n_components: int = Query(0, ge=0, description="0 = auto (≥95% varianza)"),
) -> dict:
    """
    REDDIM-1 — Principal Component Analysis.

    Si `n_components=0`, encuentra automáticamente el menor k que retiene
    ≥95% de la varianza acumulada (criterio típico del PDF).

    Devuelve la varianza explicada por componente + la proyección 2D
    de las primeras 200 filas para visualización (PC1, PC2 vs target).
    """
    X, y, cols = _prepare_xy(tabla, target)

    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA con todos los componentes para ver varianza acumulada
    pca_full = PCA()
    pca_full.fit(X_scaled)
    cum_var = np.cumsum(pca_full.explained_variance_ratio_)

    if n_components == 0:
        # Auto: menor k con cum_var >= 0.95
        n_components = int(np.searchsorted(cum_var, 0.95) + 1)
        n_components = min(n_components, len(cols))

    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)

    # 2D scatter para visualización (siempre PC1, PC2)
    pca2 = PCA(n_components=2).fit_transform(X_scaled)
    sample_size = min(500, len(y))
    rng = np.random.default_rng(42)
    idx = rng.choice(len(y), size=sample_size, replace=False)

    return {
        "table": tabla,
        "target": target,
        "n_features": len(cols),
        "n_samples": int(len(y)),
        "features": cols,
        "n_components_requested": n_components,
        "explained_variance_ratio": [float(x) for x in pca.explained_variance_ratio_],
        "cumulative_variance": [float(x) for x in cum_var[:n_components]],
        "all_components_cumvar": [float(x) for x in cum_var],
        "components_matrix": [
            [float(x) for x in row] for row in pca.components_
        ],
        "scatter_2d": {
            "pc1": [float(pca2[i, 0]) for i in idx],
            "pc2": [float(pca2[i, 1]) for i in idx],
            "target": [int(y[i]) for i in idx],
        },
    }


# ============================================================
# REDDIM-2: t-SNE
# ============================================================


@router.get("/tsne/{tabla}")
async def tsne(
    tabla: str,
    target: str = Query("failure_next_48h"),
    perplexity: int = Query(30, ge=5, le=50),
    max_rows: int = Query(2000, ge=200, le=5000),
) -> dict:
    """
    REDDIM-2 — t-SNE para visualización 2D.

    Técnica no lineal que preserva la estructura local. Muy útil para
    visualizar clusters en datasets con muchas features.

    Es O(n²) en memoria y tiempo — limitamos a `max_rows` para que el
    endpoint responda en menos de 30s.
    """
    X, y, cols = _prepare_xy(tabla, target)

    from sklearn.manifold import TSNE
    from sklearn.preprocessing import StandardScaler

    # Limitar tamaño
    n = min(max_rows, len(y))
    if n < len(y):
        rng = np.random.default_rng(42)
        idx = rng.choice(len(y), size=n, replace=False)
        X_use = X.iloc[idx].values
        y_use = y[idx]
    else:
        X_use = X.values
        y_use = y

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_use)

    tsne_model = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=42,
        n_iter=500,
        init="pca",
    )
    X_tsne = tsne_model.fit_transform(X_scaled)

    return {
        "table": tabla,
        "target": target,
        "perplexity": perplexity,
        "n_samples_used": int(n),
        "n_features": len(cols),
        "scatter_2d": {
            "x": [float(v) for v in X_tsne[:, 0]],
            "y": [float(v) for v in X_tsne[:, 1]],
            "target": [int(v) for v in y_use],
        },
        "kl_divergence": float(tsne_model.kl_divergence_),
    }


# ============================================================
# REDDIM-3: Filter (univariate)
# ============================================================


@router.get("/filter/{tabla}")
async def filter_method(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("chi2", regex="^(chi2|pearson|variance|mutual_info)$"),
    k: int = Query(5, ge=1, le=20),
) -> dict:
    """
    REDDIM-3 — Feature selection por Filter (univariate).

    Métodos:
      chi2:          chi² entre cada feature (escalada a no-negativa) y target.
      pearson:       |correlación Pearson| con target.
      variance:      varianza de cada feature (filtra features constantes).
      mutual_info:   mutual information con target (no asume linealidad).

    Devuelve ranking de features con su score, y top-k seleccionados.
    """
    X, y, cols = _prepare_xy(tabla, target)

    from sklearn.feature_selection import chi2 as sk_chi2
    from sklearn.feature_selection import mutual_info_classif
    from sklearn.preprocessing import MinMaxScaler

    if method == "chi2":
        # chi² requiere features no negativas
        X_pos = MinMaxScaler().fit_transform(X)
        scores, pvals = sk_chi2(X_pos, y)
        scores = scores.tolist()
        pvalues = pvals.tolist()
    elif method == "pearson":
        scores = [float(abs(X[c].corr(pd.Series(y)))) for c in cols]
        pvalues = None
    elif method == "variance":
        scores = [float(X[c].var()) for c in cols]
        pvalues = None
    else:  # mutual_info
        mi = mutual_info_classif(X, y, random_state=42)
        scores = mi.tolist()
        pvalues = None

    ranking = sorted(
        [{"feature": cols[i], "score": float(scores[i]),
          "pvalue": (float(pvalues[i]) if pvalues else None)} for i in range(len(cols))],
        key=lambda x: x["score"], reverse=True,
    )

    selected = [r["feature"] for r in ranking[:k]]

    return {
        "table": tabla,
        "target": target,
        "method": method,
        "k_requested": k,
        "n_features_total": len(cols),
        "ranking": ranking,
        "selected": selected,
        "dropped": [r["feature"] for r in ranking[k:]],
    }


# ============================================================
# REDDIM-4: Wrapper (Forward / Backward / RFE)
# ============================================================


@router.get("/wrapper/{tabla}")
async def wrapper(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("forward", regex="^(forward|backward|rfe)$"),
    k: int = Query(5, ge=1, le=20),
) -> dict:
    """
    REDDIM-4 — Feature selection Wrapper.

    Usa un modelo base (RandomForest) para evaluar subconjuntos de features:

      forward:  empieza vacío, añade el feature que más mejora el score.
      backward: empieza con todos, elimina el que menos perjudica.
      rfe:      Recursive Feature Elimination — ordena features por
                importancia, elimina los k peores, repite.

    Más caro que filter pero captura interacciones.
    """
    X, y, cols = _prepare_xy(tabla, target)

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_selection import (
        RFE,
        SequentialFeatureSelector,
    )
    from sklearn.preprocessing import StandardScaler

    X_scaled = StandardScaler().fit_transform(X)
    base = RandomForestClassifier(n_estimators=50, random_state=42, max_depth=8, n_jobs=-1)

    if method == "forward":
        sfs = SequentialFeatureSelector(
            base, n_features_to_select=k, direction="forward",
            scoring="roc_auc", cv=3, n_jobs=-1,
        )
        sfs.fit(X_scaled, y)
        selected_mask = sfs.get_support()
    elif method == "backward":
        sfs = SequentialFeatureSelector(
            base, n_features_to_select=k, direction="backward",
            scoring="roc_auc", cv=3, n_jobs=-1,
        )
        sfs.fit(X_scaled, y)
        selected_mask = sfs.get_support()
    else:  # rfe
        rfe = RFE(base, n_features_to_select=k, step=1)
        rfe.fit(X_scaled, y)
        selected_mask = rfe.support_

    selected = [cols[i] for i in range(len(cols)) if selected_mask[i]]
    dropped = [cols[i] for i in range(len(cols)) if not selected_mask[i]]

    return {
        "table": tabla,
        "target": target,
        "method": method,
        "k_requested": k,
        "n_features_total": len(cols),
        "selected": selected,
        "dropped": dropped,
    }


# ============================================================
# REDDIM-5: Embedded (Lasso / RF importance)
# ============================================================


@router.get("/embedded/{tabla}")
async def embedded(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("rf_importance", regex="^(lasso|rf_importance)$"),
    threshold: float = Query(0.01, ge=0.0, le=1.0),
) -> dict:
    """
    REDDIM-5 — Feature selection Embedded.

    La selección ocurre dentro del entrenamiento del modelo:

      lasso:          LogisticRegression con penalty L1. Coeficientes
                      exactamente 0 → feature descartada.
      rf_importance:  RandomForest devuelve feature_importances_; nos
                      quedamos con features con importancia > threshold.

    Sin separar entrenamiento de selección. Más rápido que wrapper.
    """
    X, y, cols = _prepare_xy(tabla, target)

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    X_scaled = StandardScaler().fit_transform(X)

    if method == "lasso":
        # LogisticRegression con L1 (saga solver)
        clf = LogisticRegression(
            penalty="l1", solver="saga", C=0.5, max_iter=2000, random_state=42,
        )
        clf.fit(X_scaled, y)
        coefs = clf.coef_[0]
        scores = [float(abs(c)) for c in coefs]
        selected_mask = [s > 0 for s in scores]
    else:  # rf_importance
        clf = RandomForestClassifier(
            n_estimators=100, random_state=42, max_depth=10, n_jobs=-1,
        )
        clf.fit(X_scaled, y)
        scores = clf.feature_importances_.tolist()
        selected_mask = [s > threshold for s in scores]

    ranking = sorted(
        [{"feature": cols[i], "score": float(scores[i])} for i in range(len(cols))],
        key=lambda x: x["score"], reverse=True,
    )
    selected = [r["feature"] for r in ranking if r["score"] > (0 if method == "lasso" else threshold)]

    return {
        "table": tabla,
        "target": target,
        "method": method,
        "threshold": threshold if method == "rf_importance" else None,
        "n_features_total": len(cols),
        "ranking": ranking,
        "selected": selected,
        "dropped": [r["feature"] for r in ranking if r["feature"] not in selected],
    }


# ============================================================
# REDDIM-6: Comparativa de las 3 familias
# ============================================================


@router.get("/compare/{tabla}")
async def compare(
    tabla: str,
    target: str = Query("failure_next_48h"),
    k: int = Query(5, ge=1, le=20),
) -> dict:
    """
    REDDIM-6 — Comparativa de filter / wrapper / embedded.

    Aplica las 3 familias con k=5 y muestra qué features eligen.
    Si una feature aparece en las 3, es muy probable que sea
    realmente importante; si solo en 1, puede ser ruido.
    """
    X, y, cols = _prepare_xy(tabla, target)

    # Reutilizamos las funciones individuales para mantener consistencia
    fil = await filter_method(tabla=tabla, target=target, method="mutual_info", k=k)
    emb = await embedded(tabla=tabla, target=target, method="rf_importance", threshold=0.05)

    # Wrapper RFE (más rápido que sequential)
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_selection import RFE
    from sklearn.preprocessing import StandardScaler
    X_scaled = StandardScaler().fit_transform(X)
    rfe = RFE(
        RandomForestClassifier(n_estimators=50, random_state=42, max_depth=8, n_jobs=-1),
        n_features_to_select=k, step=1,
    )
    rfe.fit(X_scaled, y)
    wrap_selected = [cols[i] for i in range(len(cols)) if rfe.support_[i]]

    selected_by = {
        "filter (mutual_info)": fil["selected"],
        "wrapper (RFE)":        wrap_selected,
        "embedded (RF importance)": emb["selected"][:k],  # top k
    }

    # Conteo cruzado: cuántas familias eligieron cada feature
    all_features = set()
    for s in selected_by.values():
        all_features.update(s)

    cross_count = []
    for f in all_features:
        count = sum(1 for v in selected_by.values() if f in v)
        cross_count.append({"feature": f, "selected_by_n_families": count,
                            "families": [k for k, v in selected_by.items() if f in v]})
    cross_count.sort(key=lambda x: x["selected_by_n_families"], reverse=True)

    consensus = [r["feature"] for r in cross_count if r["selected_by_n_families"] == 3]

    return {
        "table": tabla,
        "target": target,
        "k": k,
        "n_features_total": len(cols),
        "selected_by_family": selected_by,
        "cross_family_agreement": cross_count,
        "consensus_features": consensus,
        "interpretation": (
            f"{len(consensus)} feature(s) elegidas por las 3 familias "
            f"(consenso fuerte): {consensus}. Si una feature aparece en "
            f"solo 1 familia, considera si es ruido o si solo es relevante "
            f"para ese método específico."
        ),
    }
