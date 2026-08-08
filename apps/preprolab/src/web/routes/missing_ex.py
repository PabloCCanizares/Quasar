"""Bloque MISSING — scaffolds (versión alumno).

Este archivo es el punto de partida del bloque `missing` cuando
LAB_PREPROLAB no lo contiene. Cinco ejercicios que cubren las técnicas
del Tema 5 sobre valores perdidos.

Objetivos del bloque:
  1. MISSING-1: DROP — eliminar filas con .dropna() (any/all/thresh).
  2. MISSING-2: SIMPLE — imputación por media / mediana / moda.
  3. MISSING-3: KNN Imputation — buscar K instancias similares y promediar.
  4. MISSING-4: K-Means Imputation — agrupar y rellenar con el centroide.
  5. MISSING-5: COMPARE — aplicar los 4 métodos sobre una columna y
                          comparar las distribuciones resultantes.

Endpoint no-ejercicio (columns_with_nulls) se sirve desde missing.py
siempre — el alumno puede usarlo para ver qué columnas necesitan
imputación incluso sin haber empezado los ejercicios.

Flujo de trabajo:
  1. Implementa las funciones en este archivo.
  2. Ejecuta `./lab.sh preprolab restart` para recargar FastAPI.
  3. Recarga la pestaña Valores perdidos en la web.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/missing", tags=["preprolab-missing"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


# ============================================================
# Helper no-gateado (se sirve desde aquí también para no romper UI)
# ============================================================


@router.get("/columns_with_nulls/{tabla}")
async def columns_with_nulls(tabla: str) -> dict:
    """Lista qué columnas tienen al menos un null — NO es ejercicio."""
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    result = []
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n > 0:
            result.append({
                "column": col,
                "null_count": n,
                "null_pct": round(100 * n / len(df), 2),
                "dtype": str(df[col].dtype),
                "is_numeric": bool(pd.api.types.is_numeric_dtype(df[col])),
            })
    return {"table": tabla, "rows": int(len(df)), "columns": result}


# ============================================================
# MISSING-1: DROP (EJERCICIO)
# ============================================================


@router.get("/dropna/{tabla}")
async def dropna_action(
    tabla: str,
    mode: str = Query("any", regex="^(any|all|thresh)$"),
    thresh: int = Query(1, ge=1),
    subset: Optional[str] = None,
) -> dict:
    """
    EJERCICIO MISSING-1 — Eliminar filas con valores perdidos.

    Aplica `df.dropna()` con varias estrategias:
      - mode='any': elimina la fila si CUALQUIER columna es null.
      - mode='all': elimina solo si TODAS las columnas son null.
      - mode='thresh': mantiene filas con al menos `thresh` valores no-null.
      - subset: lista CSV de columnas a evaluar.

    Estructura esperada:
        {
          "table", "mode", "thresh", "subset",
          "rows_before", "rows_after",
          "rows_dropped", "rows_dropped_pct"
        }

    Pistas:
      - df.dropna(how='any'/'all', subset=cols)
      - df.dropna(thresh=N, subset=cols)
      - rows_dropped_pct = 100 * dropped / total
    """
    return _exercise_placeholder(
        "MISSING-1",
        "Implementa .dropna() con modos any/all/thresh y subset opcional. "
        "Devuelve estadísticas antes/después.",
    )


# ============================================================
# MISSING-2: SIMPLE — media / mediana / moda (EJERCICIO)
# ============================================================


@router.get("/impute_simple/{tabla}/{columna}")
async def impute_simple(
    tabla: str,
    columna: str,
    strategy: str = Query("mean", regex="^(mean|median|mode|constant)$"),
    fill_value: Optional[float] = None,
) -> dict:
    """
    EJERCICIO MISSING-2 — Imputación simple por constante (media/mediana/moda).

    Para columnas numéricas: mean | median | constant.
    Para columnas categóricas: mode | constant.

    Estructura esperada:
        {
          "table", "column", "strategy", "impute_value",
          "null_count_before", "null_count_after",
          "stats_before", "stats_after",  # {count, mean, median, std, min, max}
          "histogram_before", "histogram_after",  # {bin_edges, counts}
          "warning_variance_reduction"  # 1 - std_after / std_before
        }

    Pistas:
      - series.mean(), series.median(), series.mode().iloc[0]
      - series.fillna(impute_value)
      - El histograma se construye con numpy.histogram(clean, bins=30).
      - Recuerda devolver tipos nativos (int, float), no numpy.
      - La variance reduction es importante para que el alumno VEA que
        la media reduce la dispersión (problema del método simple).
    """
    return _exercise_placeholder(
        "MISSING-2",
        "Implementa imputación simple (mean/median/mode/constant). "
        "Devuelve histograma ANTES y DESPUÉS para visualizar el efecto.",
    )


# ============================================================
# MISSING-3: KNN Imputation (EJERCICIO)
# ============================================================


@router.get("/impute_knn/{tabla}/{columna}")
async def impute_knn(
    tabla: str,
    columna: str,
    k: int = Query(5, ge=1, le=50),
) -> dict:
    """
    EJERCICIO MISSING-3 — KNN Imputation.

    Para cada instancia con `columna` null, busca las K instancias más
    similares usando las OTRAS columnas numéricas como features y promedia
    su valor.

    Pasos típicos:
      1. Filtra columnas numéricas: numeric_cols = [c for c in df.columns
         if pd.api.types.is_numeric_dtype(df[c])]
      2. Estandariza (x - mean) / std para que la distancia no esté
         dominada por escalas grandes.
      3. Aplica sklearn.impute.KNNImputer(n_neighbors=k, weights="uniform").
      4. Des-estandariza para devolver valores en escala original.
      5. Devuelve stats + histograma ANTES y DESPUÉS, y ejemplos de
         filas concretas que fueron imputadas.

    Estructura esperada (similar a MISSING-2 + estos extras):
        {
          ..., "method": "KNN", "k": k,
          "features_used": [...],  # las otras columnas numéricas
          "examples": [
            {"row_id", "imputed_value", "other_features": {...}}, ...
          ]
        }

    Pistas:
      - `from sklearn.impute import KNNImputer`
      - `from sklearn.preprocessing import StandardScaler`
      - `series.std().replace(0, 1)` evita división por cero.
    """
    return _exercise_placeholder(
        "MISSING-3",
        "Implementa KNN Imputation con sklearn.KNNImputer. "
        "Estandariza antes y devuelve valores en escala original.",
    )


# ============================================================
# MISSING-4: K-Means Imputation (EJERCICIO)
# ============================================================


@router.get("/impute_kmeans/{tabla}/{columna}")
async def impute_kmeans(
    tabla: str,
    columna: str,
    k: int = Query(5, ge=2, le=20),
) -> dict:
    """
    EJERCICIO MISSING-4 — K-Means Imputation (KMI).

    Procedimiento (PDF del Tema 5, sección KMI):
      1. Imputación TEMPORAL con mediana (para poder ejecutar KMeans inicial).
      2. Estandarizar las features numéricas.
      3. KMeans(n_clusters=k) sobre las features estandarizadas.
      4. Des-estandarizar los centroides para tenerlos en escala original.
      5. Para cada instancia con `columna` ORIGINALMENTE null, reemplazar
         con el valor de `columna` en el centroide de su cluster.
      6. Devolver estadísticas + distribución por cluster + ejemplos.

    El PDF lo marca como "mejor balance entre calidad y escalabilidad
    para Big Data" — captura estructura de grupo mejor que la media
    global y es paralelizable.

    Estructura esperada:
        {
          ..., "method": "K-Means", "k": k,
          "features_used": [...],
          "cluster_distribution": {
            "0": {"size", "imputed_count", "centroid_value"}, ...
          },
          "examples": [{"row_id", "cluster", "imputed_value", "cluster_size"}, ...]
        }

    Pistas:
      - sklearn.cluster.KMeans(n_clusters=k, random_state=42, n_init=10)
      - scaler.inverse_transform(km.cluster_centers_) para des-estandarizar
      - Recuerda guardar el null_mask ANTES de imputar temporalmente,
        para saber qué filas hay que reemplazar al final.
    """
    return _exercise_placeholder(
        "MISSING-4",
        "Implementa K-Means Imputation: imputación temporal con mediana → "
        "KMeans → reemplazar nulls originales con centroide del cluster.",
    )


# ============================================================
# MISSING-5: COMPARE (EJERCICIO)
# ============================================================


@router.get("/compare/{tabla}/{columna}")
async def compare(tabla: str, columna: str) -> dict:
    """
    EJERCICIO MISSING-5 — Comparativa de los 4 métodos sobre una columna.

    Aplica los métodos del bloque sobre la misma columna y devuelve
    estadísticas + histogramas superpuestos para que el alumno vea
    visualmente cómo cada método distorsiona la distribución.

    Para el método 'drop' no hay imputación — devuelve la distribución
    de los valores RESTANTES (referencia limpia sin sesgo de imputación).

    Estructura esperada:
        {
          "table", "column", "null_count", "null_pct",
          "methods": {
            "drop":   {"stats", "histogram", "note"},
            "mean":   {"stats", "histogram", "note"},
            "median": {"stats", "histogram", "note"},
            "knn":    {"stats", "histogram", "note"},
            "kmeans": {"stats", "histogram", "note"}
          },
          "variance_loss_vs_drop": {"mean": ..., "median": ..., ...},
          "interpretation": {
            "best_preserve_variance": "<method>",
            "worst_preserve_variance": "<method>"
          }
        }

    Pistas:
      - Reutiliza la lógica de MISSING-1/2/3/4 internamente.
      - variance_loss = 1 - (std_imputed / std_drop).
      - El método que mejor preserva varianza SUELE ser KMeans o KNN
        (capturan estructura), no mean/median (reducen varianza).
    """
    return _exercise_placeholder(
        "MISSING-5",
        "Aplica drop/mean/median/knn/kmeans sobre la columna y compara "
        "varianza resultante. Útil pedagógicamente para ver el coste de "
        "cada método.",
    )
