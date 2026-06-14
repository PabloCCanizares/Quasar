"""Bloque OUTLIERS — soluciones.

Implementa las técnicas del Tema 5 sobre detección y gestión de
outliers + class noise filters.

Outliers numéricos (atributo):
  - OUTLIERS-1  IQR: Q1 - 1.5*IQR  /  Q3 + 1.5*IQR
  - OUTLIERS-2  Z-score: |z| > umbral (default 3.0)
  - OUTLIERS-3  Gestión: remove / cap (winsorizing) / log-transform

Class noise (etiqueta):
  - OUTLIERS-4  Noise Filters (PDF Tema 5):
      EF    (Ensemble Filter):           3 clasificadores con k-fold CV.
                                          Elimina si TODOS fallan (conservador).
      CVCF  (Cross-Validated Committees): k clasificadores DecisionTree.
                                          Elimina si > la mitad falla (moderado).
      IPF   (Iterative-Partitioning):     CVCF iterado hasta convergencia (agresivo).

El endpoint OUTLIERS-4 acepta un parámetro `inject_noise_pct` que
flippea aleatoriamente N% de las etiquetas ANTES de aplicar el filter,
para que el alumno pueda validar la precisión del detector (compara
las instancias detectadas vs las flippeadas con ground truth).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/outliers", tags=["preprolab-outliers"])


# ============================================================
# Helpers
# ============================================================

def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


# ============================================================
# OUTLIERS-1: Detección con IQR
# ============================================================


@router.get("/detect_iqr/{tabla}/{columna}")
async def detect_iqr(
    tabla: str,
    columna: str,
    multiplier: float = Query(1.5, ge=0.5, le=5.0),
) -> dict:
    """
    OUTLIERS-1 — Detección de outliers con regla IQR.

    Bounds:
      lower = Q1 - multiplier * IQR
      upper = Q3 + multiplier * IQR

    multiplier=1.5 es la convención clásica (≈ 99.3% en una normal).
    multiplier=3.0 detecta solo "outliers extremos".
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")
    if not pd.api.types.is_numeric_dtype(df[columna]):
        raise HTTPException(400, detail="IQR solo aplica a columnas numéricas")

    series = df[columna].dropna()
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    mask = (df[columna] < lower) | (df[columna] > upper)
    outlier_indices = df.index[mask].tolist()

    # Boxplot data
    box_data = {
        "min": float(series.min()),
        "q1": q1,
        "median": float(series.median()),
        "q3": q3,
        "max": float(series.max()),
        "lower_whisker": lower,
        "upper_whisker": upper,
    }

    return {
        "table": tabla,
        "column": columna,
        "method": "IQR",
        "multiplier": multiplier,
        "bounds": {"lower": lower, "upper": upper},
        "stats": {"q1": q1, "q3": q3, "iqr": iqr},
        "outlier_count": int(mask.sum()),
        "outlier_pct": round(100 * mask.sum() / len(df), 3),
        "boxplot_data": box_data,
        "outlier_samples": [
            {"row_id": int(idx), "value": float(df.at[idx, columna])}
            for idx in outlier_indices[:10]
        ],
    }


# ============================================================
# OUTLIERS-2: Detección con Z-score
# ============================================================


@router.get("/detect_zscore/{tabla}/{columna}")
async def detect_zscore(
    tabla: str,
    columna: str,
    threshold: float = Query(3.0, ge=1.0, le=5.0),
) -> dict:
    """
    OUTLIERS-2 — Detección con Z-score.

    z_i = (x_i - μ) / σ
    Outlier si |z_i| > threshold (default 3.0, ≈ 99.7% para distribución normal).

    Sensible a la presencia de outliers (rompe la media y la std).
    Para datos con muchos outliers, usar IQR (más robusto) o Z-score
    robusto (mediana + MAD).
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")
    if not pd.api.types.is_numeric_dtype(df[columna]):
        raise HTTPException(400, detail="Z-score solo aplica a columnas numéricas")

    series = df[columna].dropna()
    mean = float(series.mean())
    std = float(series.std())
    if std == 0:
        return {
            "table": tabla, "column": columna,
            "warning": "std=0, no se pueden calcular z-scores",
        }

    z_scores = (df[columna] - mean) / std
    mask = z_scores.abs() > threshold
    outlier_indices = df.index[mask & df[columna].notna()].tolist()

    return {
        "table": tabla,
        "column": columna,
        "method": "Z-score",
        "threshold": threshold,
        "stats": {"mean": mean, "std": std},
        "outlier_count": int(mask.sum()),
        "outlier_pct": round(100 * mask.sum() / len(df), 3),
        "outlier_samples": [
            {
                "row_id": int(idx),
                "value": float(df.at[idx, columna]),
                "z_score": round(float(z_scores.at[idx]), 3),
            }
            for idx in outlier_indices[:10]
        ],
    }


# ============================================================
# OUTLIERS-3: Gestión (remove / cap / log)
# ============================================================


@router.get("/handle/{tabla}/{columna}")
async def handle(
    tabla: str,
    columna: str,
    strategy: str = Query("cap", regex="^(remove|cap|log)$"),
    method: str = Query("iqr", regex="^(iqr|zscore)$"),
    multiplier: float = Query(1.5, ge=0.5, le=5.0),
    threshold: float = Query(3.0, ge=1.0, le=5.0),
) -> dict:
    """
    OUTLIERS-3 — Aplica una estrategia de gestión de outliers.

    Estrategias:
      remove: elimina filas con outliers detectados.
      cap:    winsoriza (recorta al bound) — preserva el tamaño del dataset.
      log:    aplica log1p() — útil cuando hay cola larga positiva.

    Para detectar primero usa IQR (default) o Z-score.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")
    if not pd.api.types.is_numeric_dtype(df[columna]):
        raise HTTPException(400, detail="solo numéricas")

    series_orig = df[columna]
    clean = series_orig.dropna()

    # Detección
    if method == "iqr":
        q1 = clean.quantile(0.25)
        q3 = clean.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
    else:  # zscore
        mean = clean.mean()
        std = clean.std()
        lower = mean - threshold * std
        upper = mean + threshold * std

    mask_outlier = (series_orig < lower) | (series_orig > upper)
    outlier_count_before = int(mask_outlier.sum())

    # Aplicación
    if strategy == "remove":
        new_series = series_orig[~mask_outlier]
        new_df_size = len(new_series)
    elif strategy == "cap":
        new_series = series_orig.clip(lower=lower, upper=upper)
        new_df_size = len(new_series)
    else:  # log
        # log1p para soportar 0 — si hay negativos, desplazamos
        if clean.min() < 0:
            shift = -float(clean.min()) + 1
            new_series = np.log1p(series_orig + shift)
        else:
            new_series = np.log1p(series_orig)
        new_df_size = len(new_series)

    return {
        "table": tabla,
        "column": columna,
        "strategy": strategy,
        "detection_method": method,
        "bounds": {"lower": float(lower), "upper": float(upper)},
        "outlier_count_before": outlier_count_before,
        "rows_before": len(series_orig),
        "rows_after": new_df_size,
        "stats_before": {
            "mean": float(clean.mean()), "std": float(clean.std()),
            "min": float(clean.min()), "max": float(clean.max()),
        },
        "stats_after": {
            "mean": float(new_series.dropna().mean()),
            "std": float(new_series.dropna().std()),
            "min": float(new_series.dropna().min()),
            "max": float(new_series.dropna().max()),
        },
        "histogram_before": _hist(clean),
        "histogram_after": _hist(new_series.dropna()),
    }


def _hist(s: pd.Series, bins: int = 30) -> dict:
    if len(s) == 0:
        return {"bin_edges": [], "counts": []}
    counts, edges = np.histogram(s, bins=bins)
    return {
        "bin_edges": [float(x) for x in edges],
        "counts": [int(x) for x in counts],
    }


# ============================================================
# OUTLIERS-4: Class noise filters (EF / CVCF / IPF)
# ============================================================


@router.get("/noise_filter/{tabla}")
async def noise_filter(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("ef", regex="^(ef|cvcf|ipf)$"),
    k: int = Query(5, ge=3, le=10),
    inject_noise_pct: float = Query(0.0, ge=0.0, le=0.30),
) -> dict:
    """
    OUTLIERS-4 — Class Noise Filters del Tema 5.

    Detecta instancias con etiqueta probablemente incorrecta usando
    varios clasificadores en k-fold CV.

    Métodos:
      ef:   Ensemble Filter — 3 clasificadores (DecisionTree, KNN, LDA).
            Marca como ruido si TODOS fallan. Conservador.
      cvcf: Cross-Validated Committees Filter — k clasificadores
            DecisionTree con k-fold. Marca si > la mitad falla. Moderado.
      ipf:  Iterative-Partitioning Filter — CVCF iterado hasta
            estabilización del nº de ruidosas. Agresivo.

    Parámetro inject_noise_pct: flippea aleatoriamente N% de las
    etiquetas antes de aplicar el filter, para que el alumno valide
    la precisión del detector con ground truth.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if target not in df.columns:
        raise HTTPException(404, detail=f"Target desconocido: {target}")

    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.model_selection import StratifiedKFold
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier

    # Solo trabajamos con filas completas en numéricas (drop nulls para no
    # tener que imputar en este bloque — usaríamos el de missing antes).
    numeric_cols = [c for c in _numeric_columns(df) if c != target]
    sub = df[numeric_cols + [target]].dropna().reset_index(drop=True)

    if len(sub) < 100:
        raise HTTPException(400, detail="Necesitamos al menos 100 filas completas para CV")

    X = sub[numeric_cols].values
    y = sub[target].astype(int).values

    # Inyección opcional de ruido sintético
    rng = np.random.default_rng(42)
    y_clean = y.copy()
    injected_indices: set[int] = set()
    if inject_noise_pct > 0:
        n_flip = int(len(y) * inject_noise_pct)
        flip_idx = rng.choice(len(y), size=n_flip, replace=False)
        for i in flip_idx:
            y[i] = 1 - y[i]  # flip binario
            injected_indices.add(int(i))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Función auxiliar: predicciones out-of-fold de un clasificador
    def _oof_predict(clf_factory) -> np.ndarray:
        preds = np.zeros(len(y), dtype=int)
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        for train_idx, test_idx in skf.split(X_scaled, y):
            clf = clf_factory()
            clf.fit(X_scaled[train_idx], y[train_idx])
            preds[test_idx] = clf.predict(X_scaled[test_idx])
        return preds

    if method == "ef":
        # Ensemble Filter: 3 clasificadores, marca si los 3 fallan
        preds_dt  = _oof_predict(lambda: DecisionTreeClassifier(random_state=42, max_depth=8))
        preds_knn = _oof_predict(lambda: KNeighborsClassifier(n_neighbors=1))
        preds_lda = _oof_predict(LinearDiscriminantAnalysis)
        fail_dt  = preds_dt  != y
        fail_knn = preds_knn != y
        fail_lda = preds_lda != y
        noise_mask = fail_dt & fail_knn & fail_lda
        per_classifier = {
            "DecisionTree": int(fail_dt.sum()),
            "KNN(1)":       int(fail_knn.sum()),
            "LDA":          int(fail_lda.sum()),
        }
        iterations = 1
    elif method == "cvcf":
        # k clasificadores DecisionTree (uno por fold), mayoría
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        all_preds = []
        for fold, (train_idx, _) in enumerate(skf.split(X_scaled, y)):
            clf = DecisionTreeClassifier(random_state=42 + fold, max_depth=8)
            clf.fit(X_scaled[train_idx], y[train_idx])
            all_preds.append(clf.predict(X_scaled))
        # votación por mayoría
        votes_wrong = np.zeros(len(y))
        for preds in all_preds:
            votes_wrong += (preds != y)
        noise_mask = votes_wrong > (k / 2)
        per_classifier = {f"DT_fold{i}": int((all_preds[i] != y).sum()) for i in range(k)}
        iterations = 1
    else:  # ipf
        # Iterative-Partitioning Filter: aplica CVCF hasta convergencia
        y_iter = y.copy()
        X_iter = X_scaled.copy()
        active_mask = np.ones(len(y), dtype=bool)
        last_n_noise = -1
        iterations = 0
        max_iterations = 5
        cumulative_noise = np.zeros(len(y), dtype=bool)

        while iterations < max_iterations:
            iterations += 1
            active_idx = np.where(active_mask)[0]
            if len(active_idx) < 100:
                break
            X_act = X_iter[active_idx]
            y_act = y_iter[active_idx]
            skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42 + iterations)
            all_preds = []
            for fold, (tr, _) in enumerate(skf.split(X_act, y_act)):
                clf = DecisionTreeClassifier(random_state=42 + fold + iterations * 100, max_depth=8)
                clf.fit(X_act[tr], y_act[tr])
                all_preds.append(clf.predict(X_act))
            votes_wrong = np.zeros(len(y_act))
            for preds in all_preds:
                votes_wrong += (preds != y_act)
            iter_noise_local = votes_wrong > (k / 2)
            # Mapear de vuelta a índices globales
            iter_noise_global = active_idx[iter_noise_local]
            cumulative_noise[iter_noise_global] = True
            active_mask[iter_noise_global] = False
            n_noise = int(iter_noise_local.sum())
            if n_noise == last_n_noise or n_noise == 0:
                break
            last_n_noise = n_noise

        noise_mask = cumulative_noise
        per_classifier = None

    # Métricas si hubo inyección
    metrics = None
    if injected_indices:
        injected_set = injected_indices
        detected_set = set(int(i) for i in np.where(noise_mask)[0])
        tp = len(injected_set & detected_set)
        fp = len(detected_set - injected_set)
        fn = len(injected_set - detected_set)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        metrics = {
            "injected": len(injected_set),
            "detected": len(detected_set),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(2 * precision * recall / (precision + recall), 3) if (precision + recall) > 0 else 0.0,
        }

    # Distribución por clase
    noisy_by_class = {}
    for cls in np.unique(y):
        cls_mask = (y == int(cls))
        noisy_by_class[str(int(cls))] = {
            "total": int(cls_mask.sum()),
            "noisy": int((noise_mask & cls_mask).sum()),
            "pct": round(100 * (noise_mask & cls_mask).sum() / max(1, cls_mask.sum()), 2),
        }

    return {
        "table": tabla,
        "target": target,
        "method": method,
        "k": k,
        "iterations": iterations,
        "inject_noise_pct": inject_noise_pct,
        "n_samples": int(len(y)),
        "n_features": int(len(numeric_cols)),
        "features": numeric_cols,
        "noisy_count": int(noise_mask.sum()),
        "noisy_pct": round(100 * noise_mask.sum() / len(y), 2),
        "per_classifier_failures": per_classifier,
        "by_class": noisy_by_class,
        "validation_metrics": metrics,
    }
