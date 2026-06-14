"""Bloque EDA — soluciones.

Endpoints de Análisis Exploratorio de Datos sobre las 4 tablas de la flota
de robots. Cubre los conceptos del Tema 5 EDA: análisis univariable,
bivariable, correlaciones y missing matrix.

Hay dos clases de endpoints:

1. **No-gateados** (siempre disponibles, no son ejercicio):
     - GET /api/preprolab/eda/overview
     - GET /api/preprolab/eda/schema/{tabla}
   El alumno los puede usar para explorar el dataset sin tener nada
   implementado todavía.

2. **Gateados** (los 3 ejercicios del bloque):
     - EDA-1: univariate(tabla, columna)
     - EDA-2: missing(tabla)
     - EDA-3: correlations(tabla)
   Si LAB_PREPROLAB no contiene 'eda', analytics.py importa eda_ex.py
   (scaffolds) para estos tres.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from src.web.data_loader import TABLES, is_seeded, load_table

router = APIRouter(prefix="/api/preprolab/eda", tags=["preprolab-eda"])


# ============================================================
# Helpers de inspección de tipos
# ============================================================

def _column_type(series: pd.Series) -> str:
    """Clasifica una columna como 'numeric' | 'categorical' | 'datetime' | 'text'.

    No es el dtype literal de pandas — agrupa por uso analítico:
      - numeric:     int, float (incluyendo nulls)
      - categorical: object con <= 50 valores únicos
      - text:        object con > 50 valores únicos (descripcion, etc.)
      - datetime:    columnas que parecen fechas (heurístico)
    """
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    # object → categorical o text según cardinalidad
    nunique = series.nunique(dropna=True)
    if nunique <= 50:
        return "categorical"
    return "text"


def _safe_jsonify(obj: Any) -> Any:
    """Convierte tipos numpy/pandas a tipos nativos serializables."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if pd.isna(obj):
        return None
    return obj


# ============================================================
# Endpoints no-gateados
# ============================================================


@router.get("/overview")
async def overview() -> dict:
    """Resumen general del dataset: rows/cols por tabla + variable objetivo."""
    if not is_seeded():
        raise HTTPException(
            status_code=503,
            detail="Dataset no generado. Ejecuta `./lab.sh preprolab seed`.",
        )

    summary = {}
    for name in TABLES:
        df = load_table(name)
        types_count = {}
        for col in df.columns:
            t = _column_type(df[col])
            types_count[t] = types_count.get(t, 0) + 1
        summary[name] = {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "types_count": types_count,
        }

    # Variable objetivo en robots
    robots = load_table("robots")
    target_counts = robots["failure_next_48h"].value_counts().to_dict()

    return {
        "tables": summary,
        "target": {
            "name": "failure_next_48h",
            "table": "robots",
            "counts": {str(k): int(v) for k, v in target_counts.items()},
        },
    }


@router.get("/schema/{tabla}")
async def schema(tabla: str) -> dict:
    """Esquema detallado de una tabla: por columna, tipo y muestra de valores."""
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")

    df = load_table(tabla)
    columns = []
    for col in df.columns:
        series = df[col]
        col_type = _column_type(series)
        sample_values = series.dropna().head(5).tolist()
        # Limpiar tipos numpy
        sample_values = [_safe_jsonify(v) for v in sample_values]
        columns.append({
            "name": col,
            "type": col_type,
            "dtype": str(series.dtype),
            "nunique": int(series.nunique(dropna=True)),
            "null_count": int(series.isna().sum()),
            "sample_values": sample_values,
        })

    return {
        "table": tabla,
        "rows": int(len(df)),
        "columns": columns,
    }


# ============================================================
# EDA-1: Análisis univariable (ejercicio)
# ============================================================


@router.get("/univariate/{tabla}/{columna}")
async def univariate(tabla: str, columna: str) -> dict:
    """
    EDA-1 — Análisis univariable de una columna.

    Devuelve estadísticas descriptivas y datos para histograma (numéricas) o
    value_counts (categóricas).
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")

    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")

    series = df[columna]
    col_type = _column_type(series)

    result: dict = {
        "table": tabla,
        "column": columna,
        "type": col_type,
        "count": int(series.count()),
        "null_count": int(series.isna().sum()),
        "null_pct": round(100 * series.isna().sum() / len(series), 2),
    }

    if col_type == "numeric":
        clean = series.dropna()
        if len(clean) == 0:
            result["error"] = "columna totalmente vacía"
            return result
        # Estadísticas básicas
        result["stats"] = {
            "mean": float(clean.mean()),
            "median": float(clean.median()),
            "std": float(clean.std()),
            "min": float(clean.min()),
            "max": float(clean.max()),
            "q1": float(clean.quantile(0.25)),
            "q3": float(clean.quantile(0.75)),
        }
        # Histograma con numpy (más fiable que pandas.hist para JSON)
        counts, bin_edges = np.histogram(clean, bins=30)
        result["histogram"] = {
            "bin_edges": [float(x) for x in bin_edges],
            "counts": [int(x) for x in counts],
        }
        # Detección rápida de outliers IQR (informativo, NO es el ejercicio del bloque outliers)
        iqr = result["stats"]["q3"] - result["stats"]["q1"]
        lower = result["stats"]["q1"] - 1.5 * iqr
        upper = result["stats"]["q3"] + 1.5 * iqr
        result["outliers_iqr"] = {
            "lower_bound": float(lower),
            "upper_bound": float(upper),
            "count": int(((clean < lower) | (clean > upper)).sum()),
        }
    elif col_type in ("categorical", "text"):
        # value_counts para categóricas (top 30 si hay muchas)
        vc = series.value_counts(dropna=False).head(30)
        result["value_counts"] = {
            str(k): int(v) for k, v in vc.items()
        }
        result["unique_count"] = int(series.nunique(dropna=True))
    else:  # datetime u otros
        result["note"] = f"Columna de tipo '{col_type}' — análisis específico no implementado."

    return result


# ============================================================
# EDA-2: Missing matrix (ejercicio)
# ============================================================


@router.get("/missing/{tabla}")
async def missing(tabla: str) -> dict:
    """
    EDA-2 — Missing matrix de una tabla.

    Para cada columna, calcula count, null_count y null_pct. También calcula
    co-ocurrencia: pares de columnas que tienden a ser null juntas
    (indicador de MAR/MNAR estructural).
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")

    df = load_table(tabla)
    n = len(df)

    # Por columna
    per_column = []
    for col in df.columns:
        nc = int(df[col].isna().sum())
        per_column.append({
            "column": col,
            "count": n - nc,
            "null_count": nc,
            "null_pct": round(100 * nc / n, 2) if n > 0 else 0,
        })

    # Co-ocurrencia: pares de columnas con nulls correlacionados
    # Sólo entre columnas con al menos 1 null.
    null_cols = [c["column"] for c in per_column if c["null_count"] > 0]
    co_occurrence = []
    if len(null_cols) >= 2:
        # Matriz binaria de "es null"
        null_mask = df[null_cols].isna()
        for i, a in enumerate(null_cols):
            for b in null_cols[i + 1:]:
                both_null = int((null_mask[a] & null_mask[b]).sum())
                if both_null > 0:
                    co_occurrence.append({
                        "col_a": a,
                        "col_b": b,
                        "both_null_count": both_null,
                        "both_null_pct": round(100 * both_null / n, 2),
                    })
        # Ordenar por co-ocurrencia descendente
        co_occurrence.sort(key=lambda x: x["both_null_count"], reverse=True)

    return {
        "table": tabla,
        "rows": n,
        "per_column": per_column,
        "co_occurrence": co_occurrence[:20],  # top 20 pares
        "interpretation": _interpret_missing(per_column, co_occurrence),
    }


def _interpret_missing(per_column: list[dict], co_occurrence: list[dict]) -> dict:
    """Heurística para sugerir el mecanismo de pérdida (MCAR/MAR/MNAR)."""
    totally_missing = [c for c in per_column if c["null_pct"] >= 95]
    high_missing = [c for c in per_column if 20 <= c["null_pct"] < 95]
    low_missing = [c for c in per_column if 0 < c["null_pct"] < 20]

    hints = []
    if totally_missing:
        hints.append(
            f"Columnas casi siempre null ({', '.join(c['column'] for c in totally_missing)}) "
            f"sugieren MNAR estructural (la fuente no reporta este campo)."
        )
    if high_missing:
        hints.append(
            f"Columnas con 20-95% null ({', '.join(c['column'] for c in high_missing)}) "
            f"sugieren MAR (dependen de otra variable observada)."
        )
    if low_missing and not high_missing:
        hints.append(
            f"Columnas con pocos null ({', '.join(c['column'] for c in low_missing[:5])}) "
            f"sugieren MCAR (pérdida aleatoria)."
        )
    return {"hints": hints}


# ============================================================
# EDA-3: Correlaciones (ejercicio)
# ============================================================


@router.get("/correlations/{tabla}")
async def correlations(tabla: str) -> dict:
    """
    EDA-3 — Matriz de correlaciones Pearson de columnas numéricas.

    Detecta redundancia (pares con |r| > 0.9) que el alumno luego puede usar
    para feature selection en el bloque reduce_dim.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")

    df = load_table(tabla)

    # Quedarse con columnas numéricas únicamente
    numeric_cols = [c for c in df.columns if _column_type(df[c]) == "numeric"]
    if len(numeric_cols) < 2:
        return {
            "table": tabla,
            "error": "La tabla tiene menos de 2 columnas numéricas — no hay correlaciones que calcular.",
            "numeric_columns": numeric_cols,
        }

    # Pearson — pandas hace dropna por pares automáticamente
    corr = df[numeric_cols].corr(method="pearson")

    # Matriz como lista de listas (Plotly necesita esto para Heatmap)
    matrix = [
        [None if pd.isna(v) else round(float(v), 4) for v in corr.iloc[i].values]
        for i in range(len(corr))
    ]

    # Pares más correlacionados (excluyendo diagonal)
    top_pairs = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if i >= j:
                continue
            v = corr.iloc[i, j]
            if pd.isna(v):
                continue
            top_pairs.append({"col_a": a, "col_b": b, "corr": round(float(v), 4)})
    top_pairs.sort(key=lambda x: abs(x["corr"]), reverse=True)

    # Detectar redundancia clara (|r| > 0.9)
    redundant = [p for p in top_pairs if abs(p["corr"]) > 0.9]

    return {
        "table": tabla,
        "columns": cols,
        "matrix": matrix,
        "top_pairs": top_pairs[:10],
        "redundant_pairs": redundant,
    }
