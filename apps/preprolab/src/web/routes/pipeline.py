"""Pipeline Studio — Fase 11.

Permite componer pipelines de preprocesamiento aplicando los bloques del
Tema 5 en orden, entrenar un RandomForest sobre el resultado y comparar
N pipelines lado a lado por AUC/F1/precision/recall/ROC.

Es el hito final de PreproLab: junta TODO lo aprendido en los bloques
anteriores en una sola interfaz comparativa.

Endpoint clave:
  POST /api/preprolab/pipeline/run    Configura, ejecuta, devuelve métricas
  GET  /api/preprolab/pipeline/list   Lista pipelines guardados en cache
  POST /api/preprolab/pipeline/clear  Borra el cache

Configuración aceptada en `run`:
{
  "name": "Pipeline A",
  "missing": "drop" | "mean" | "median" | "knn" | "kmeans" | "none",
  "outliers": "none" | "iqr_cap" | "zscore_cap" | "iqr_remove",
  "normalize": "none" | "zscore" | "minmax" | "robust",
  "reduce_dim": "none" | "pca",
  "pca_n_components": int,
  "balance": "none" | "undersample" | "oversample"
}
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.web.data_loader import load_table

router = APIRouter(prefix="/api/preprolab/pipeline", tags=["preprolab-pipeline"])

TABLE = "robots"
TARGET = "failure_next_48h"

# Cache en memoria de pipelines ejecutados (para comparativa)
_pipelines_cache: list[dict] = []


# ============================================================
# Schema de configuración
# ============================================================

class PipelineConfig(BaseModel):
    name: str = Field(..., description="Nombre identificador del pipeline")
    missing: str = Field("drop", pattern="^(drop|mean|median|knn|kmeans|none)$")
    outliers: str = Field("none", pattern="^(none|iqr_cap|zscore_cap|iqr_remove)$")
    normalize: str = Field("none", pattern="^(none|zscore|minmax|robust)$")
    reduce_dim: str = Field("none", pattern="^(none|pca)$")
    pca_n_components: int = Field(0, ge=0, le=20)
    balance: str = Field("none", pattern="^(none|undersample|oversample)$")
    test_size: float = Field(0.25, gt=0.05, lt=0.5)
    seed: int = Field(42)


# ============================================================
# Pipeline executor
# ============================================================

def _apply_missing(df: pd.DataFrame, method: str, numeric_cols: list[str]) -> pd.DataFrame:
    if method == "none":
        return df
    if method == "drop":
        return df.dropna()
    df = df.copy()
    if method in ("mean", "median"):
        for c in numeric_cols:
            if df[c].isna().any():
                value = df[c].mean() if method == "mean" else df[c].median()
                df[c] = df[c].fillna(value)
        return df
    if method == "knn":
        from sklearn.impute import KNNImputer
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X = df[numeric_cols]
        means = X.mean()
        stds = X.std().replace(0, 1)
        X_scaled = (X - means) / stds
        knn = KNNImputer(n_neighbors=5)
        X_imp = pd.DataFrame(knn.fit_transform(X_scaled), columns=numeric_cols, index=df.index)
        X_imp = X_imp * stds + means
        df[numeric_cols] = X_imp
        return df
    if method == "kmeans":
        from sklearn.cluster import KMeans
        X = df[numeric_cols]
        X_temp = X.fillna(X.median())
        km = KMeans(n_clusters=5, random_state=42, n_init=10)
        labels = km.fit_predict(X_temp)
        centroids = pd.DataFrame(km.cluster_centers_, columns=numeric_cols)
        for c in numeric_cols:
            mask = df[c].isna()
            for idx in df.index[mask]:
                df.at[idx, c] = centroids.iloc[labels[df.index.get_loc(idx)]][c]
        return df
    return df


def _apply_outliers(df: pd.DataFrame, method: str, numeric_cols: list[str]) -> pd.DataFrame:
    if method == "none":
        return df
    df = df.copy()
    for c in numeric_cols:
        s = df[c].dropna()
        if method == "iqr_cap":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            df[c] = df[c].clip(lower=lo, upper=hi)
        elif method == "zscore_cap":
            mean, std = s.mean(), s.std() or 1
            lo, hi = mean - 3 * std, mean + 3 * std
            df[c] = df[c].clip(lower=lo, upper=hi)
        elif method == "iqr_remove":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            df = df[(df[c].isna()) | ((df[c] >= lo) & (df[c] <= hi))]
    return df


def _apply_normalize(X: pd.DataFrame, method: str) -> pd.DataFrame:
    if method == "none":
        return X
    if method == "zscore":
        return (X - X.mean()) / X.std().replace(0, 1)
    if method == "minmax":
        rng = (X.max() - X.min()).replace(0, 1)
        return (X - X.min()) / rng
    if method == "robust":
        iqr = (X.quantile(0.75) - X.quantile(0.25)).replace(0, 1)
        return (X - X.median()) / iqr
    return X


def _apply_balance(X: pd.DataFrame, y: pd.Series, strategy: str, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    if strategy == "none":
        return X, y
    df = X.copy()
    df["_y"] = y.values
    sizes = df.groupby("_y").size()
    target_size = int(sizes.min()) if strategy == "undersample" else int(sizes.max())
    parts = []
    for cls, group in df.groupby("_y"):
        if strategy == "undersample" and len(group) > target_size:
            parts.append(group.sample(n=target_size, random_state=seed))
        elif strategy == "oversample" and len(group) < target_size:
            parts.append(group.sample(n=target_size, replace=True, random_state=seed))
        else:
            parts.append(group)
    out = pd.concat(parts).reset_index(drop=True)
    return out.drop(columns=["_y"]), out["_y"]


@router.post("/run")
async def run(config: PipelineConfig) -> dict:
    """Ejecuta el pipeline configurado y devuelve métricas + ROC."""
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
        roc_curve,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    t0 = time.time()
    df = load_table(TABLE)
    initial_rows = len(df)

    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and c != TARGET
    ]

    # Paso 1: missing
    df = _apply_missing(df, config.missing, numeric_cols)
    after_missing = len(df)

    # Si quedan nulls tras imputación parcial, drop final
    df = df[numeric_cols + [TARGET]].dropna()
    after_clean = len(df)

    if len(df) < 100:
        raise HTTPException(400, detail=f"Pipeline deja solo {len(df)} filas — insuficiente")

    # Paso 2: outliers
    df = _apply_outliers(df, config.outliers, numeric_cols)
    after_outliers = len(df)

    X = df[numeric_cols]
    y = df[TARGET]

    # Paso 3: normalize
    X_norm = _apply_normalize(X, config.normalize)

    # Paso 4: reduce_dim (PCA)
    if config.reduce_dim == "pca":
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_norm)
        n_comp = config.pca_n_components if config.pca_n_components > 0 else min(len(numeric_cols), 5)
        pca_model = PCA(n_components=n_comp)
        X_final = pca_model.fit_transform(X_scaled)
        feature_names = [f"PC{i+1}" for i in range(n_comp)]
        explained_var = float(pca_model.explained_variance_ratio_.sum())
    else:
        X_final = X_norm.values
        feature_names = numeric_cols
        explained_var = 1.0

    # Paso 5: balance (solo sobre train, no test)
    X_train, X_test, y_train, y_test = train_test_split(
        X_final, y.values, test_size=config.test_size, stratify=y.values, random_state=config.seed
    )

    # Aplicar balance solo en train
    if config.balance != "none":
        X_tr_df = pd.DataFrame(X_train, columns=feature_names)
        X_tr_df, y_train_s = _apply_balance(X_tr_df, pd.Series(y_train), config.balance, config.seed)
        X_train = X_tr_df.values
        y_train = y_train_s.values

    # Paso 6: train + evaluate
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=8, random_state=config.seed, n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]

    auc = float(roc_auc_score(y_test, y_proba))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    accuracy = float(accuracy_score(y_test, y_pred))
    cm = confusion_matrix(y_test, y_pred).tolist()

    # ROC curve sampling
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    # Submuestreo si hay muchos puntos
    if len(fpr) > 50:
        idx = np.linspace(0, len(fpr) - 1, 50).astype(int)
        fpr_s = fpr[idx]
        tpr_s = tpr[idx]
    else:
        fpr_s = fpr
        tpr_s = tpr

    elapsed = round(time.time() - t0, 2)

    result = {
        "name": config.name,
        "config": config.model_dump(),
        "rows_initial": initial_rows,
        "rows_after_missing": after_missing,
        "rows_after_clean": after_clean,
        "rows_after_outliers": after_outliers,
        "rows_train": int(len(X_train)),
        "rows_test": int(len(X_test)),
        "features_final": feature_names,
        "explained_variance": explained_var,
        "metrics": {
            "auc": round(auc, 4),
            "f1": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "accuracy": round(accuracy, 4),
        },
        "confusion_matrix": cm,
        "roc_curve": {
            "fpr": [float(x) for x in fpr_s],
            "tpr": [float(x) for x in tpr_s],
        },
        "elapsed_seconds": elapsed,
    }

    # Cachear para comparar
    _pipelines_cache.append(result)
    if len(_pipelines_cache) > 20:
        _pipelines_cache.pop(0)

    return result


@router.get("/list")
async def list_pipelines() -> dict:
    """Lista pipelines en cache (resumen sin curva ROC)."""
    summary = [
        {
            "name": p["name"],
            "config": p["config"],
            "rows_train": p["rows_train"],
            "metrics": p["metrics"],
            "elapsed_seconds": p["elapsed_seconds"],
        }
        for p in _pipelines_cache
    ]
    return {"count": len(summary), "pipelines": summary}


@router.get("/compare")
async def compare() -> dict:
    """Devuelve los pipelines en cache con curvas ROC para superponer."""
    return {"count": len(_pipelines_cache), "pipelines": _pipelines_cache}


@router.post("/clear")
async def clear() -> dict:
    """Vacía el cache de pipelines."""
    n = len(_pipelines_cache)
    _pipelines_cache.clear()
    return {"cleared": n}
