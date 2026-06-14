"""Bloque EDA — scaffolds (versión alumno).

Este archivo es el punto de partida del bloque `eda` cuando LAB_PREPROLAB
no lo contiene. La aplicación importa estos endpoints y muestra
"ejercicio sin resolver" hasta que sustituyas el cuerpo de cada función.

Objetivos del bloque:
  1. EDA-1: análisis univariable (estadísticas + histograma / value_counts).
  2. EDA-2: missing matrix (null_pct por columna + co-ocurrencia de nulls).
  3. EDA-3: matriz de correlaciones Pearson + pares redundantes.

Endpoints no-ejercicio (overview, schema): siempre se sirven desde eda.py.
Aquí sólo viven los tres endpoints que SÍ son ejercicio.

Flujo de trabajo:
  1. Implementa las funciones en este archivo.
  2. Ejecuta `./lab.sh preprolab restart` para recargar FastAPI.
  3. Recarga la pestaña EDA en la web.

No uses `./lab.sh preprolab unlock eda` salvo que seas profesor y quieras
cargar la solución oficial.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from src.web.data_loader import TABLES, is_seeded, load_table

router = APIRouter(prefix="/api/preprolab/eda", tags=["preprolab-eda"])


# ============================================================
# Helpers (compartidos con la solución, no son ejercicio)
# ============================================================

def _column_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    nunique = series.nunique(dropna=True)
    if nunique <= 50:
        return "categorical"
    return "text"


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    """Respuesta estándar de scaffold sin resolver."""
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


# ============================================================
# Endpoints no-gateados (idénticos a eda.py — se sirven siempre)
# ============================================================


@router.get("/overview")
async def overview() -> dict:
    """Resumen general — NO es ejercicio, se sirve igual."""
    if not is_seeded():
        raise HTTPException(503, detail="Dataset no generado. Ejecuta `./lab.sh preprolab seed`.")

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
    """Esquema de una tabla — NO es ejercicio, se sirve igual."""
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    columns = []
    for col in df.columns:
        series = df[col]
        sample = series.dropna().head(5).tolist()
        sample = [v.item() if hasattr(v, "item") else v for v in sample]
        columns.append({
            "name": col,
            "type": _column_type(series),
            "dtype": str(series.dtype),
            "nunique": int(series.nunique(dropna=True)),
            "null_count": int(series.isna().sum()),
            "sample_values": sample,
        })
    return {"table": tabla, "rows": int(len(df)), "columns": columns}


# ============================================================
# EDA-1: Análisis univariable (EJERCICIO)
# ============================================================


@router.get("/univariate/{tabla}/{columna}")
async def univariate(tabla: str, columna: str) -> dict:
    """
    EJERCICIO EDA-1 — Análisis univariable de una columna.

    Devuelve estadísticas descriptivas y datos para visualizar la distribución.

    Para columnas NUMÉRICAS, el dict debe incluir:
        {
          "table": tabla, "column": columna, "type": "numeric",
          "count": int (no-null), "null_count": int, "null_pct": float,
          "stats": {"mean", "median", "std", "min", "max", "q1", "q3"},
          "histogram": {"bin_edges": [...], "counts": [...]}
        }

    Para columnas CATEGÓRICAS:
        {
          ..., "type": "categorical",
          "value_counts": {valor: count},  # top 30
          "unique_count": int
        }

    Pistas:
      - Usa `series.dropna()` antes de calcular stats numéricos.
      - `series.quantile(0.25)` y `series.quantile(0.75)` para Q1 y Q3.
      - `numpy.histogram(clean, bins=30)` devuelve (counts, bin_edges).
      - Para categóricas, `series.value_counts(dropna=False).head(30)`.
      - El frontend espera tipos nativos de Python — convierte numpy con `int()` y `float()`.
    """
    return _exercise_placeholder(
        "EDA-1",
        "Implementa análisis univariable: stats (mean/median/std/min/max/q1/q3) "
        "+ histograma o value_counts según el tipo de columna."
    )


# ============================================================
# EDA-2: Missing matrix (EJERCICIO)
# ============================================================


@router.get("/missing/{tabla}")
async def missing(tabla: str) -> dict:
    """
    EJERCICIO EDA-2 — Missing matrix de una tabla.

    Por cada columna, calcula:
      - count: registros no-null
      - null_count: registros null
      - null_pct: porcentaje de null

    Y además, co-ocurrencia: para cada par de columnas con al menos 1 null,
    cuántas filas tienen AMBAS columnas null simultáneamente. Este patrón
    indica MAR o MNAR estructural.

    Estructura esperada:
        {
          "table": tabla, "rows": n,
          "per_column": [{"column", "count", "null_count", "null_pct"}, ...],
          "co_occurrence": [{"col_a", "col_b", "both_null_count", "both_null_pct"}, ...]
        }

    Pistas:
      - `df[col].isna().sum()` da el null_count de una columna.
      - Para co-ocurrencia, una máscara booleana `df[null_cols].isna()` y
        `(mask[a] & mask[b]).sum()` cuentan filas con ambas null.
      - Sólo te interesan los pares con al menos 1 co-ocurrencia (filtra).
      - Ordena el resultado por `both_null_count` descendente.
    """
    return _exercise_placeholder(
        "EDA-2",
        "Implementa missing matrix: null_pct por columna + co-ocurrencia "
        "de nulls por pares de columnas."
    )


# ============================================================
# EDA-3: Correlaciones (EJERCICIO)
# ============================================================


@router.get("/correlations/{tabla}")
async def correlations(tabla: str) -> dict:
    """
    EJERCICIO EDA-3 — Matriz de correlaciones Pearson + pares redundantes.

    Calcula la matriz de correlaciones (PCC) sobre las columnas NUMÉRICAS y
    devuelve también la lista ordenada de pares más correlacionados (en
    valor absoluto). Detecta redundancia con |r| > 0.9.

    Estructura esperada:
        {
          "table": tabla,
          "columns": ["bateria_pct", "voltaje_v", ...],
          "matrix": [[1.0, 0.99, ...], ...],  # NxN, valores entre -1 y 1
          "top_pairs": [{"col_a", "col_b", "corr"}, ...],  # top 10
          "redundant_pairs": [{"col_a", "col_b", "corr"}, ...]  # |r| > 0.9
        }

    Pistas:
      - Filtra columnas numéricas: `[c for c in df.columns if _column_type(df[c]) == "numeric"]`.
      - `df[numeric_cols].corr(method="pearson")` devuelve la matriz como DataFrame.
      - Itera con `i < j` para evitar duplicados y la diagonal.
      - Sustituye NaN por None al serializar (el JSON no soporta NaN).
      - El frontend usará la matriz para un heatmap Plotly.
    """
    return _exercise_placeholder(
        "EDA-3",
        "Implementa matriz Pearson + pares con |r|>0.9. Útil para detectar "
        "redundancia (bateria_pct ~ voltaje_v ~ consumo_total_kwh)."
    )
