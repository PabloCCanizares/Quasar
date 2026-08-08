"""Bloque REDUCE_DIM — scaffolds (versión alumno).

Seis ejercicios sobre reducción de dimensionalidad y feature selection
del Tema 5:

  REDDIM-1  pca         PCA con auto-selección de componentes (>=95%)
  REDDIM-2  tsne        t-SNE 2D para visualización
  REDDIM-3  filter      Chi², Pearson, varianza, mutual_info
  REDDIM-4  wrapper     Forward / Backward / RFE
  REDDIM-5  embedded    Lasso L1 / RandomForest feature_importances_
  REDDIM-6  compare     Aplica filter+wrapper+embedded, muestra consenso

Flujo:
  1. Implementa las funciones aquí.
  2. ./lab.sh preprolab restart
  3. Recarga la pestaña Reducción dim.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/reduce_dim", tags=["preprolab-reduce_dim"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


@router.get("/pca/{tabla}")
async def pca(
    tabla: str,
    target: str = Query("failure_next_48h"),
    n_components: int = Query(0, ge=0),
) -> dict:
    """
    EJERCICIO REDDIM-1 — Principal Component Analysis.

    Si n_components=0, encuentra el k mínimo que retiene ≥95% varianza.

    Estructura esperada:
        {
          "table", "target",
          "n_features", "n_samples", "features",
          "n_components_requested",
          "explained_variance_ratio": [...],
          "cumulative_variance": [...],
          "all_components_cumvar": [...],
          "components_matrix": [[...], ...],
          "scatter_2d": {"pc1", "pc2", "target"}  # primeras 500 filas
        }

    Pistas:
      - Estandarizar antes (StandardScaler): PCA es sensible a escala.
      - PCA() sin args → todos los componentes; PCA(n) → primeros n.
      - cum_var = np.cumsum(pca.explained_variance_ratio_).
      - np.searchsorted(cum_var, 0.95) + 1 = primer k con ≥95%.
    """
    return _exercise_placeholder(
        "REDDIM-1",
        "Implementa PCA con escalado previo y selección automática del k "
        "que conserva ≥95% de la varianza. Devuelve scatter 2D para "
        "visualizar PC1 vs PC2 coloreado por target.",
    )


@router.get("/tsne/{tabla}")
async def tsne(
    tabla: str,
    target: str = Query("failure_next_48h"),
    perplexity: int = Query(30, ge=5, le=50),
    max_rows: int = Query(2000, ge=200, le=5000),
) -> dict:
    """
    EJERCICIO REDDIM-2 — t-SNE 2D para visualización.

    Técnica no lineal, O(n²) en memoria — limita a max_rows.

    Estructura esperada:
        {
          "table", "target", "perplexity",
          "n_samples_used", "n_features",
          "scatter_2d": {"x": [...], "y": [...], "target": [...]},
          "kl_divergence": float
        }

    Pistas:
      - sklearn.manifold.TSNE(n_components=2, perplexity, init="pca").
      - Si len(X) > max_rows, muestrear con rng.choice(replace=False).
      - kl_divergence_ es atributo del modelo entrenado.
    """
    return _exercise_placeholder(
        "REDDIM-2",
        "Implementa t-SNE 2D con muestreo si hay >max_rows filas. "
        "Devuelve scatter 2D coloreado por target.",
    )


@router.get("/filter/{tabla}")
async def filter_method(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("chi2", regex="^(chi2|pearson|variance|mutual_info)$"),
    k: int = Query(5, ge=1, le=20),
) -> dict:
    """
    EJERCICIO REDDIM-3 — Feature selection univariate (Filter).

    Métodos:
      chi2:          sklearn.feature_selection.chi2 (necesita features ≥ 0).
      pearson:       |correlación Pearson| con target.
      variance:      varianza de cada feature.
      mutual_info:   sklearn.feature_selection.mutual_info_classif.

    Estructura esperada:
        {
          "table", "target", "method", "k_requested",
          "n_features_total",
          "ranking": [{"feature", "score", "pvalue"}, ...],
          "selected": [top k features],
          "dropped": [resto]
        }

    Pistas:
      - chi² requiere features no negativas → MinMaxScaler antes.
      - Pearson con un binario: |df[c].corr(pd.Series(y))|.
      - Devolver ranking ordenado descendente por score.
    """
    return _exercise_placeholder(
        "REDDIM-3",
        "Implementa filter con 4 métodos. Recuerda: chi² requiere "
        "features no-negativas (MinMaxScaler antes).",
    )


@router.get("/wrapper/{tabla}")
async def wrapper(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("forward", regex="^(forward|backward|rfe)$"),
    k: int = Query(5, ge=1, le=20),
) -> dict:
    """
    EJERCICIO REDDIM-4 — Feature selection Wrapper.

    Usa un modelo base para evaluar subconjuntos.

    Estructura esperada:
        {
          "table", "target", "method", "k_requested",
          "n_features_total",
          "selected": [...], "dropped": [...]
        }

    Pistas:
      - SequentialFeatureSelector(estimator, n_features_to_select=k,
        direction="forward"|"backward", scoring="roc_auc", cv=3).
      - RFE(estimator, n_features_to_select=k, step=1).
      - Estandarizar antes con StandardScaler.
      - Estimator: RandomForestClassifier(n_estimators=50, max_depth=8).
    """
    return _exercise_placeholder(
        "REDDIM-4",
        "Implementa forward/backward/RFE con sklearn. CV=3 para que "
        "el endpoint responda en tiempo razonable.",
    )


@router.get("/embedded/{tabla}")
async def embedded(
    tabla: str,
    target: str = Query("failure_next_48h"),
    method: str = Query("rf_importance", regex="^(lasso|rf_importance)$"),
    threshold: float = Query(0.01, ge=0.0, le=1.0),
) -> dict:
    """
    EJERCICIO REDDIM-5 — Feature selection Embedded.

    Selección dentro del entrenamiento:
      lasso:          LogisticRegression(penalty='l1', solver='saga').
                      Coef exactamente 0 → feature descartada.
      rf_importance:  RandomForestClassifier.feature_importances_;
                      mantener si importance > threshold.

    Estructura esperada:
        {
          "table", "target", "method", "threshold",
          "n_features_total",
          "ranking": [{"feature", "score"}, ...],
          "selected": [...], "dropped": [...]
        }

    Pistas:
      - Estandarizar antes de Lasso (L1 sensible a escala).
      - LogisticRegression(penalty='l1', solver='saga', C=0.5, max_iter=2000).
      - Lasso: selected = features con |coef| > 0.
      - RF: importancias suman 1, threshold=0.05 es típico.
    """
    return _exercise_placeholder(
        "REDDIM-5",
        "Implementa Lasso L1 (LogisticRegression penalty='l1') o "
        "RF feature_importances_. Estandariza antes para Lasso.",
    )


@router.get("/compare/{tabla}")
async def compare(
    tabla: str,
    target: str = Query("failure_next_48h"),
    k: int = Query(5, ge=1, le=20),
) -> dict:
    """
    EJERCICIO REDDIM-6 — Comparativa de las 3 familias.

    Aplica filter + wrapper + embedded sobre la misma tabla y devuelve
    qué features prioriza cada familia + consenso (las que aparecen en
    las 3).

    Estructura esperada:
        {
          "table", "target", "k", "n_features_total",
          "selected_by_family": {"filter (...)", "wrapper (...)", "embedded (...)"},
          "cross_family_agreement": [
            {"feature", "selected_by_n_families", "families": [...]}
          ],
          "consensus_features": [...],
          "interpretation": str
        }

    Pistas:
      - Usa mutual_info para filter (no lineal, más robusto que Pearson).
      - Usa RFE para wrapper (más rápido que sequential).
      - Usa rf_importance para embedded (no necesita escalar igual que Lasso).
      - Consensus = features en TODAS las familias.
    """
    return _exercise_placeholder(
        "REDDIM-6",
        "Aplica las 3 familias y devuelve qué features están en consenso "
        "(elegidas por las 3). Las consensus son muy probablemente las "
        "más informativas.",
    )
