"""Bloque OUTLIERS — scaffolds (versión alumno).

Cuatro ejercicios que cubren las técnicas del Tema 5 sobre outliers
y class noise filters.

Ejercicios:
  OUTLIERS-1  detect_iqr        Detección con regla IQR.
  OUTLIERS-2  detect_zscore     Detección con Z-score.
  OUTLIERS-3  handle            Gestión: remove / cap / log.
  OUTLIERS-4  noise_filter      EF / CVCF / IPF sobre target.

Flujo de trabajo:
  1. Implementa las funciones en este archivo.
  2. Ejecuta `./lab.sh preprolab restart` para recargar FastAPI.
  3. Recarga la pestaña Outliers en la web.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/outliers", tags=["preprolab-outliers"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


# ============================================================
# OUTLIERS-1: Detección con IQR (EJERCICIO)
# ============================================================


@router.get("/detect_iqr/{tabla}/{columna}")
async def detect_iqr(
    tabla: str,
    columna: str,
    multiplier: float = Query(1.5, ge=0.5, le=5.0),
) -> dict:
    """
    EJERCICIO OUTLIERS-1 — Detección de outliers con regla IQR.

    Calcula los bounds:
        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR
    donde IQR = Q3 - Q1.

    Estructura esperada:
        {
          "table", "column", "method": "IQR", "multiplier",
          "bounds": {"lower", "upper"},
          "stats": {"q1", "q3", "iqr"},
          "outlier_count": int, "outlier_pct": float,
          "boxplot_data": {"min", "q1", "median", "q3", "max",
                            "lower_whisker", "upper_whisker"},
          "outlier_samples": [{"row_id", "value"}, ...]  # primeros 10
        }

    Pistas:
      - series.quantile(0.25) y series.quantile(0.75).
      - mask = (df[col] < lower) | (df[col] > upper).
      - boxplot_data tiene min/max RAW pero whiskers = bounds.
    """
    return _exercise_placeholder(
        "OUTLIERS-1",
        "Implementa detección IQR. bounds = Q1 - mult*IQR, Q3 + mult*IQR. "
        "Devuelve count, pct, samples y boxplot_data.",
    )


# ============================================================
# OUTLIERS-2: Detección con Z-score (EJERCICIO)
# ============================================================


@router.get("/detect_zscore/{tabla}/{columna}")
async def detect_zscore(
    tabla: str,
    columna: str,
    threshold: float = Query(3.0, ge=1.0, le=5.0),
) -> dict:
    """
    EJERCICIO OUTLIERS-2 — Detección con Z-score.

    z_i = (x_i - μ) / σ
    Outlier si |z_i| > threshold.

    Estructura esperada:
        {
          "table", "column", "method": "Z-score", "threshold",
          "stats": {"mean", "std"},
          "outlier_count", "outlier_pct",
          "outlier_samples": [{"row_id", "value", "z_score"}, ...]
        }

    Pistas:
      - Si std == 0, devolver un warning (todos los valores son iguales).
      - z_scores = (df[col] - mean) / std.
      - mask = z_scores.abs() > threshold.
      - Recuerda excluir nulls antes del cálculo.
    """
    return _exercise_placeholder(
        "OUTLIERS-2",
        "Implementa Z-score: (x - mean) / std. Outlier si |z| > threshold.",
    )


# ============================================================
# OUTLIERS-3: Gestión (EJERCICIO)
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
    EJERCICIO OUTLIERS-3 — Gestión de outliers.

    Estrategias:
      remove: filas con outliers se eliminan.
      cap:    winsorize (recorta al bound) — preserva el tamaño.
      log:    log1p() — útil con cola larga positiva. Para datos con
              valores negativos, desplaza primero.

    Detección con IQR (default) o Z-score.

    Estructura esperada:
        {
          "table", "column", "strategy", "detection_method",
          "bounds": {"lower", "upper"},
          "outlier_count_before", "rows_before", "rows_after",
          "stats_before", "stats_after",  # mean, std, min, max
          "histogram_before", "histogram_after"
        }

    Pistas:
      - cap: series.clip(lower=lower, upper=upper)
      - log con datos negativos: shift = -min + 1 antes de log1p.
      - El histograma se construye con numpy.histogram(data, bins=30).
    """
    return _exercise_placeholder(
        "OUTLIERS-3",
        "Implementa remove/cap/log. cap = clip(lower, upper). "
        "log = log1p(). remove = filtra el dataset.",
    )


# ============================================================
# OUTLIERS-4: Class noise filters (EJERCICIO)
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
    EJERCICIO OUTLIERS-4 — Class Noise Filters (PDF Tema 5).

    Detecta instancias con etiqueta probablemente incorrecta usando
    múltiples clasificadores en k-fold CV.

    Métodos:
      ef:   Ensemble Filter — 3 clasificadores (DecisionTree, KNN(1), LDA).
            Una instancia es ruidosa si TODOS la clasifican mal.
            Esquema CONSERVADOR (pocas falsas detecciones).
      cvcf: Cross-Validated Committees — k DecisionTree con k-fold.
            Ruidosa si MÁS DE LA MITAD la clasifica mal. Esquema MODERADO.
      ipf:  Iterative-Partitioning Filter — aplica CVCF iterativamente
            hasta convergencia (nº ruidosas se estabiliza). AGRESIVO.

    Parámetro inject_noise_pct: para que el alumno pueda VALIDAR el
    filter, flippea N% de etiquetas antes de aplicarlo. Si el filter
    funciona, debe detectar mayoritariamente las que tú flippeaste.

    Estructura esperada:
        {
          "table", "target", "method", "k", "iterations",
          "inject_noise_pct", "n_samples", "n_features", "features",
          "noisy_count", "noisy_pct",
          "per_classifier_failures": {clasificador: count} | None,
          "by_class": {clase: {total, noisy, pct}, ...},
          "validation_metrics": {  # solo si inject_noise_pct > 0
            "injected", "detected", "true_positives",
            "false_positives", "false_negatives",
            "precision", "recall", "f1"
          } | None
        }

    Pistas:
      - sklearn: DecisionTreeClassifier, KNeighborsClassifier(n_neighbors=1),
        LinearDiscriminantAnalysis.
      - sklearn.model_selection.StratifiedKFold(n_splits=k, shuffle=True).
      - Out-of-fold predictions: itera sobre splits, entrena con train,
        predice test_idx → preds[test_idx] = clf.predict(X[test_idx]).
      - EF: noise_mask = fail_dt & fail_knn & fail_lda.
      - CVCF: votos_mal_clasificados > k/2.
      - IPF: aplica CVCF, marca ruido, repite con resto. Para cuando
        n_noise = 0 o se estabiliza.
      - Para inject_noise_pct: usa np.random.default_rng(42) y flippea
        binario y[i] = 1 - y[i].
      - Validation: TP = injected ∩ detected, FP = detected - injected,
        FN = injected - detected.
    """
    return _exercise_placeholder(
        "OUTLIERS-4",
        "Implementa noise filter EF/CVCF/IPF con sklearn + k-fold CV. "
        "Soporta inject_noise_pct para validar con ground truth.",
    )
