"""Bloque NORMALIZE — soluciones.

Implementa las técnicas de normalización del Tema 5:

  NORM-1  zscore       x' = (x - μ) / σ                — StandardScaler
  NORM-2  minmax       x' = (x - min) / (max - min)    — MinMaxScaler [0, 1]
  NORM-3  robust       x' = (x - mediana) / IQR        — RobustScaler
  NORM-4  decimal      x' = x / 10^j                    — escalado decimal
  NORM-5  compare      aplica los 4 sobre la misma columna y compara
                       sensibilidad a outliers + rango resultante

Notas:
  - Equivalentes en Spark MLlib: pyspark.ml.feature.{StandardScaler,
    MinMaxScaler, RobustScaler}. Decimal scaling no es nativo pero se
    implementa en una línea.
  - El comparador muestra explícitamente la vulnerabilidad Min-Max a
    outliers: con [10, 20, 30, 40, 1000] → [0.0, 0.01, 0.02, 0.03, 1.0].
    El 99% de los datos queda comprimido en el 3% del rango.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/normalize", tags=["preprolab-normalize"])


# ============================================================
# Helpers
# ============================================================

def _hist(s: pd.Series, bins: int = 30) -> dict:
    clean = s.dropna()
    if len(clean) == 0:
        return {"bin_edges": [], "counts": []}
    counts, edges = np.histogram(clean, bins=bins)
    return {
        "bin_edges": [float(x) for x in edges],
        "counts": [int(x) for x in counts],
    }


def _stats(s: pd.Series) -> dict:
    clean = s.dropna()
    if len(clean) == 0:
        return {"empty": True}
    return {
        "count": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std()),
        "min": float(clean.min()),
        "max": float(clean.max()),
        "q1": float(clean.quantile(0.25)),
        "q3": float(clean.quantile(0.75)),
    }


def _check_numeric(tabla: str, columna: str) -> pd.DataFrame:
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")
    if not pd.api.types.is_numeric_dtype(df[columna]):
        raise HTTPException(400, detail="normalize solo aplica a numéricas")
    return df


# ============================================================
# NORM-1: Z-score (StandardScaler)
# ============================================================


@router.get("/zscore/{tabla}/{columna}")
async def zscore(tabla: str, columna: str) -> dict:
    """
    NORM-1 — Estandarización Z-score.

    x' = (x - μ) / σ

    Resultado: media ≈ 0, std ≈ 1. Sensible a outliers (σ se infla con
    valores extremos). El PDF lo señala como problema.
    """
    df = _check_numeric(tabla, columna)
    s = df[columna]
    clean = s.dropna()

    mean = float(clean.mean())
    std = float(clean.std())
    if std == 0:
        return {"table": tabla, "column": columna, "warning": "std=0, no se puede normalizar"}

    normalized = (s - mean) / std

    return {
        "table": tabla,
        "column": columna,
        "method": "zscore",
        "parameters": {"mean": mean, "std": std},
        "stats_before": _stats(s),
        "stats_after": _stats(normalized),
        "histogram_before": _hist(s),
        "histogram_after": _hist(normalized),
        "outlier_sensitivity_note": (
            "Z-score es sensible a outliers: std se infla con valores extremos, "
            "lo que reduce la separación entre el resto de datos en el espacio "
            "normalizado."
        ),
    }


# ============================================================
# NORM-2: Min-Max (MinMaxScaler)
# ============================================================


@router.get("/minmax/{tabla}/{columna}")
async def minmax(tabla: str, columna: str) -> dict:
    """
    NORM-2 — Min-Max scaling a [0, 1].

    x' = (x - min) / (max - min)

    Conserva la proporción relativa pero comprime cuando hay outliers.
    Ejemplo del PDF: [10, 20, 30, 40, 1000] → [0, 0.01, 0.02, 0.03, 1.0].
    """
    df = _check_numeric(tabla, columna)
    s = df[columna]
    clean = s.dropna()

    mn = float(clean.min())
    mx = float(clean.max())
    rng = mx - mn
    if rng == 0:
        return {"table": tabla, "column": columna, "warning": "rango=0, no se puede normalizar"}

    normalized = (s - mn) / rng

    # Diagnóstico de compresión: porcentaje de datos en [0, 0.1]
    pct_in_lower_decile = float((normalized <= 0.1).sum() / clean.count() * 100)

    return {
        "table": tabla,
        "column": columna,
        "method": "minmax",
        "parameters": {"min": mn, "max": mx, "range": rng},
        "stats_before": _stats(s),
        "stats_after": _stats(normalized),
        "histogram_before": _hist(s),
        "histogram_after": _hist(normalized),
        "compression_diagnostic": {
            "pct_data_in_0_0.1": round(pct_in_lower_decile, 2),
            "interpretation": (
                f"{pct_in_lower_decile:.1f}% de los datos quedan en el primer 10% del rango. "
                f"Si este valor supera ~30%, hay outliers comprimiendo la mayoría "
                f"de los datos en una franja pequeña — considera usar Robust o "
                f"limpiar outliers primero."
            ),
        },
        "outlier_sensitivity_note": (
            "Min-Max es muy sensible a outliers: un solo valor extremo expande "
            "el rango, comprimiendo el resto de datos en un intervalo diminuto."
        ),
    }


# ============================================================
# NORM-3: Robust (mediana + IQR)
# ============================================================


@router.get("/robust/{tabla}/{columna}")
async def robust(tabla: str, columna: str) -> dict:
    """
    NORM-3 — Robust scaling.

    x' = (x - mediana) / IQR

    Usa estadísticos robustos (mediana e IQR) en lugar de mean/std.
    Recomendado cuando hay outliers porque éstos no distorsionan ni la
    mediana ni el IQR. Equivalente a sklearn.RobustScaler.
    """
    df = _check_numeric(tabla, columna)
    s = df[columna]
    clean = s.dropna()

    median = float(clean.median())
    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1
    if iqr == 0:
        return {"table": tabla, "column": columna, "warning": "IQR=0, no se puede normalizar"}

    normalized = (s - median) / iqr

    return {
        "table": tabla,
        "column": columna,
        "method": "robust",
        "parameters": {"median": median, "q1": q1, "q3": q3, "iqr": iqr},
        "stats_before": _stats(s),
        "stats_after": _stats(normalized),
        "histogram_before": _hist(s),
        "histogram_after": _hist(normalized),
        "outlier_sensitivity_note": (
            "Robust resiste outliers porque la mediana y el IQR no se ven "
            "afectados por valores extremos. Recomendado cuando los datos "
            "tienen outliers conocidos o desconocidos."
        ),
    }


# ============================================================
# NORM-4: Decimal Scaling
# ============================================================


@router.get("/decimal/{tabla}/{columna}")
async def decimal(tabla: str, columna: str) -> dict:
    """
    NORM-4 — Decimal Scaling.

    x' = x / 10^j   donde j = menor entero tal que max(|x'|) < 1.

    Útil cuando los valores son grandes y mantienen proporcionalidad.
    Es la normalización más sencilla pero no centra los datos (no resta
    media ni mediana).
    """
    df = _check_numeric(tabla, columna)
    s = df[columna]
    clean = s.dropna()

    max_abs = float(clean.abs().max())
    if max_abs == 0:
        return {"table": tabla, "column": columna, "warning": "max(|x|)=0, no se puede normalizar"}

    # j = ceil(log10(max_abs))
    j = int(np.ceil(np.log10(max_abs))) if max_abs >= 1 else 0
    divisor = 10 ** j
    normalized = s / divisor

    return {
        "table": tabla,
        "column": columna,
        "method": "decimal",
        "parameters": {"j": j, "divisor": divisor, "max_abs_original": max_abs},
        "stats_before": _stats(s),
        "stats_after": _stats(normalized),
        "histogram_before": _hist(s),
        "histogram_after": _hist(normalized),
        "outlier_sensitivity_note": (
            "Decimal Scaling es proporcional a la magnitud, no centra los datos. "
            "Si max es un outlier, el divisor es demasiado grande y comprime "
            "el resto. Útil cuando los valores son grandes pero proporcionales."
        ),
    }


# ============================================================
# NORM-5: Comparativa de los 4 métodos
# ============================================================


@router.get("/compare/{tabla}/{columna}")
async def compare(tabla: str, columna: str) -> dict:
    """
    NORM-5 — Comparativa de los 4 métodos sobre la misma columna.

    Aplica zscore / minmax / robust / decimal y compara:
      - Rango resultante (min, max)
      - Std resultante
      - Compresión: % de datos en distintos cuantiles
      - Sensibilidad a outliers (comparando antes/después)

    Útil para que el alumno VEA visualmente el problema del Min-Max con
    outliers que el PDF describe ("99% de datos comprimidos en [0, 0.03]").
    """
    df = _check_numeric(tabla, columna)
    s = df[columna].dropna()

    if len(s) == 0:
        return {"table": tabla, "column": columna, "error": "columna vacía"}

    # 1. Z-score
    mean = s.mean()
    std = s.std() if s.std() != 0 else 1.0
    z = (s - mean) / std

    # 2. Min-Max
    mn, mx = s.min(), s.max()
    rng = mx - mn if mx != mn else 1.0
    mm = (s - mn) / rng

    # 3. Robust
    median = s.median()
    iqr = s.quantile(0.75) - s.quantile(0.25)
    iqr = iqr if iqr != 0 else 1.0
    rb = (s - median) / iqr

    # 4. Decimal
    max_abs = s.abs().max()
    j = int(np.ceil(np.log10(max_abs))) if max_abs >= 1 else 0
    dc = s / (10 ** j)

    methods = {
        "zscore":  {"series": z,  "params": {"mean": float(mean), "std": float(std)}},
        "minmax":  {"series": mm, "params": {"min": float(mn), "max": float(mx)}},
        "robust":  {"series": rb, "params": {"median": float(median), "iqr": float(iqr)}},
        "decimal": {"series": dc, "params": {"j": j}},
    }

    results = {}
    for name, info in methods.items():
        normalized = info["series"]
        results[name] = {
            "params": info["params"],
            "stats": _stats(normalized),
            "histogram": _hist(normalized),
            "compression_at_0_0.1": round(
                float(((normalized >= 0) & (normalized <= 0.1)).sum() / len(normalized) * 100),
                2,
            ),
        }

    # Interpretación final
    minmax_compression = results["minmax"]["compression_at_0_0.1"]
    interpretation = []
    if minmax_compression > 30:
        interpretation.append(
            f"Min-Max comprime el {minmax_compression}% de los datos en el "
            f"primer 10% del rango → hay outliers sesgando el escalado."
        )
    if results["robust"]["stats"]["std"] < results["zscore"]["stats"]["std"] * 0.5:
        interpretation.append(
            "Robust devuelve std mucho menor que Z-score → confirma presencia "
            "de outliers (Z-score se infla, Robust los ignora)."
        )

    return {
        "table": tabla,
        "column": columna,
        "n": int(len(s)),
        "original_stats": _stats(s),
        "methods": results,
        "interpretation": interpretation or ["Distribución relativamente uniforme — los 4 métodos dan resultados similares."],
        "summary_table": [
            {
                "method": name,
                "min": round(results[name]["stats"]["min"], 4),
                "max": round(results[name]["stats"]["max"], 4),
                "std": round(results[name]["stats"]["std"], 4),
                "pct_in_0_0.1": results[name]["compression_at_0_0.1"],
            }
            for name in ["zscore", "minmax", "robust", "decimal"]
        ],
    }
