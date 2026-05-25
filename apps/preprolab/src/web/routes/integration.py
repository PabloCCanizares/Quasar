"""Bloque INTEGRATION — soluciones.

Implementa las técnicas del Tema 5 sobre integración de datos:

  - INTEG-1  union              concatenación vertical de DataFrames con
                                mismo schema (con detección de incompatibilidades)
  - INTEG-2  join               4 tipos de unión: inner / left / right / outer
  - INTEG-3  find_redundancy    detección de columnas redundantes mediante
                                Pearson (numéricas) + Cramér's V (categóricas)
  - INTEG-4  dedup_by_corr      elimina columnas con |corr| > threshold,
                                eligiendo cuál conservar por heurística

Sobre el coeficiente Phi:
  Phi = sqrt(chi² / n) para variables BINARIAS. Para categóricas con
  más de 2 valores usamos Cramér's V = sqrt(chi² / (n · min(c-1, r-1))).
  Es la generalización natural del Phi y devuelve también en [0, 1].

Sobre union vs los 4 joins:
  Las 4 tablas del seed (robots, sensors_readings, events, maintenances)
  comparten la columna robot_id como FK. El endpoint join soporta cualquier
  par y muestra cómo cambia el resultado según el modo. union se usa cuando
  tenemos schemas iguales (por ejemplo, dos volcados temporales de events).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/integration", tags=["preprolab-integration"])


# ============================================================
# Helpers
# ============================================================

def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _categorical_columns(df: pd.DataFrame, max_unique: int = 50) -> list[str]:
    """Columnas tratables como categóricas (object o numeric pero con pocos valores únicos)."""
    out = []
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]) and df[c].nunique() <= max_unique:
            out.append(c)
    return out


def _cramers_v(s1: pd.Series, s2: pd.Series) -> float:
    """Cramér's V — generalización del coeficiente Phi para categóricas.

    Phi se define solo para 2x2; Cramér's V extiende a tablas r×c y
    devuelve también en [0, 1] (0 = independencia, 1 = asociación perfecta).
    """
    # Tabla de contingencia (sin NaN)
    pair = pd.DataFrame({"a": s1, "b": s2}).dropna()
    if len(pair) == 0:
        return 0.0
    contingency = pd.crosstab(pair["a"], pair["b"])
    if contingency.shape[0] < 2 or contingency.shape[1] < 2:
        return 0.0

    # Chi² manual (sin scipy para no añadir dependencia)
    observed = contingency.values
    n = observed.sum()
    row_totals = observed.sum(axis=1, keepdims=True)
    col_totals = observed.sum(axis=0, keepdims=True)
    expected = row_totals @ col_totals / n
    chi2 = np.sum((observed - expected) ** 2 / np.where(expected == 0, 1, expected))

    min_dim = min(observed.shape[0] - 1, observed.shape[1] - 1)
    if min_dim == 0:
        return 0.0
    return float(np.sqrt(chi2 / (n * min_dim)))


# ============================================================
# INTEG-1: UNION
# ============================================================


@router.get("/union/{tabla_a}/{tabla_b}")
async def union(
    tabla_a: str,
    tabla_b: str,
    same_schema_only: bool = Query(True),
) -> dict:
    """
    INTEG-1 — Concatenación vertical (union).

    Concatena dos tablas apilando filas. Si los schemas no son idénticos,
    devuelve un análisis de incompatibilidades + (si `same_schema_only=False`)
    intenta un union "permisivo" con columnas comunes solamente.
    """
    if tabla_a not in TABLES or tabla_b not in TABLES:
        raise HTTPException(404, detail="Una de las tablas no existe")

    df_a = load_table(tabla_a)
    df_b = load_table(tabla_b)

    cols_a = set(df_a.columns)
    cols_b = set(df_b.columns)
    common = sorted(cols_a & cols_b)
    only_a = sorted(cols_a - cols_b)
    only_b = sorted(cols_b - cols_a)

    schemas_match = (cols_a == cols_b)

    result = {
        "table_a": tabla_a,
        "table_b": tabla_b,
        "rows_a": int(len(df_a)),
        "rows_b": int(len(df_b)),
        "schemas_match": schemas_match,
        "common_columns": common,
        "only_in_a": only_a,
        "only_in_b": only_b,
    }

    if schemas_match:
        # Union normal
        unioned = pd.concat([df_a, df_b], ignore_index=True)
        result["unioned_rows"] = int(len(unioned))
        result["mode"] = "strict_union"
    elif not same_schema_only and common:
        # Union permisivo: solo columnas comunes
        unioned = pd.concat([df_a[common], df_b[common]], ignore_index=True)
        result["unioned_rows"] = int(len(unioned))
        result["mode"] = "common_columns_only"
        result["warning"] = (
            f"Schemas distintos. Se ha hecho union solo sobre {len(common)} "
            f"columnas comunes; se han descartado {len(only_a)} columnas de "
            f"{tabla_a} y {len(only_b)} de {tabla_b}."
        )
    else:
        result["mode"] = "blocked"
        result["error_msg"] = (
            "Schemas incompatibles. Usa same_schema_only=false para forzar "
            "un union sobre columnas comunes (perderás información)."
        )

    return result


# ============================================================
# INTEG-2: JOIN
# ============================================================


@router.get("/join/{tabla_a}/{tabla_b}")
async def join(
    tabla_a: str,
    tabla_b: str,
    on: str = Query(..., description="Columna clave (debe existir en ambas)"),
    how: str = Query("inner", regex="^(inner|left|right|outer)$"),
) -> dict:
    """
    INTEG-2 — Los 4 tipos de unión (JOIN SQL):

      inner: filas con coincidencia en AMBAS tablas
      left:  todas las filas de A + matched de B (NaN si no hay match)
      right: todas las filas de B + matched de A
      outer: todas las filas de ambas (NaN donde no hay match)
    """
    if tabla_a not in TABLES or tabla_b not in TABLES:
        raise HTTPException(404, detail="Una de las tablas no existe")

    df_a = load_table(tabla_a)
    df_b = load_table(tabla_b)

    if on not in df_a.columns:
        raise HTTPException(400, detail=f"Columna {on} no existe en {tabla_a}")
    if on not in df_b.columns:
        raise HTTPException(400, detail=f"Columna {on} no existe en {tabla_b}")

    joined = pd.merge(df_a, df_b, on=on, how=how, suffixes=("_a", "_b"))

    # Diagnósticos: cardinalidad del join
    keys_a = set(df_a[on].dropna().unique())
    keys_b = set(df_b[on].dropna().unique())
    keys_common = keys_a & keys_b

    # Muestra de filas resultantes (primeras 5, columnas reducidas)
    sample_cols = [on] + [c for c in joined.columns if c != on][:6]
    sample = (
        joined[sample_cols]
        .head(5)
        .replace({np.nan: None})
        .to_dict("records")
    )

    return {
        "table_a": tabla_a,
        "table_b": tabla_b,
        "on": on,
        "how": how,
        "rows_a": int(len(df_a)),
        "rows_b": int(len(df_b)),
        "rows_joined": int(len(joined)),
        "keys_in_a": int(len(keys_a)),
        "keys_in_b": int(len(keys_b)),
        "keys_in_common": int(len(keys_common)),
        "keys_only_in_a": int(len(keys_a - keys_b)),
        "keys_only_in_b": int(len(keys_b - keys_a)),
        "columns_after_join": list(joined.columns),
        "sample": sample,
    }


# ============================================================
# INTEG-3: FIND REDUNDANCY (Pearson + Cramér's V)
# ============================================================


@router.get("/find_redundancy/{tabla}")
async def find_redundancy(
    tabla: str,
    threshold: float = Query(0.9, ge=0.5, le=1.0),
) -> dict:
    """
    INTEG-3 — Detecta columnas redundantes en una tabla:

      - Para PARES NUMÉRICOS: Pearson PCC; redundantes si |r| > threshold.
      - Para PARES CATEGÓRICOS: Cramér's V; redundantes si V > threshold.

    Devuelve también la lista de "atributos candidatos a eliminar"
    aplicando una heurística: en cada par redundante, conservar la
    columna con mayor varianza (numéricas) o con más cardinalidad
    (categóricas).
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")

    df = load_table(tabla)

    num_cols = _numeric_columns(df)
    cat_cols = _categorical_columns(df)

    numeric_pairs = []
    if len(num_cols) >= 2:
        corr = df[num_cols].corr(method="pearson")
        for i, a in enumerate(num_cols):
            for j, b in enumerate(num_cols):
                if i >= j:
                    continue
                r = corr.iloc[i, j]
                if pd.isna(r):
                    continue
                if abs(r) > threshold:
                    numeric_pairs.append({"col_a": a, "col_b": b, "corr": round(float(r), 4)})
        numeric_pairs.sort(key=lambda p: abs(p["corr"]), reverse=True)

    categorical_pairs = []
    for i, a in enumerate(cat_cols):
        for j, b in enumerate(cat_cols):
            if i >= j:
                continue
            v = _cramers_v(df[a], df[b])
            if v > threshold:
                categorical_pairs.append({"col_a": a, "col_b": b, "cramers_v": round(v, 4)})
    categorical_pairs.sort(key=lambda p: p["cramers_v"], reverse=True)

    # Heurística de eliminación
    drop_candidates = _suggest_drops(df, numeric_pairs, categorical_pairs)

    return {
        "table": tabla,
        "threshold": threshold,
        "numeric_columns_analyzed": num_cols,
        "categorical_columns_analyzed": cat_cols,
        "redundant_numeric_pairs": numeric_pairs,
        "redundant_categorical_pairs": categorical_pairs,
        "drop_candidates": drop_candidates,
        "interpretation": {
            "numeric_count": len(numeric_pairs),
            "categorical_count": len(categorical_pairs),
            "note": (
                "Pares con |Pearson| > threshold (numéricas) o Cramér's V > threshold "
                "(categóricas). Se sugiere eliminar uno de cada par para evitar "
                "multicolinealidad. Para numéricas conservamos la de mayor varianza "
                "(mantiene poder discriminativo); para categóricas conservamos la "
                "de mayor cardinalidad."
            ),
        },
    }


def _suggest_drops(
    df: pd.DataFrame,
    numeric_pairs: list[dict],
    categorical_pairs: list[dict],
) -> list[dict]:
    """Para cada par redundante, decide qué columna eliminar."""
    suggestions = []
    keep_set: set[str] = set()
    drop_set: set[str] = set()

    for p in numeric_pairs:
        a, b = p["col_a"], p["col_b"]
        if a in drop_set or b in drop_set:
            continue
        # Comparar varianza
        var_a = df[a].var()
        var_b = df[b].var()
        if pd.isna(var_a) or pd.isna(var_b):
            continue
        drop = b if var_a >= var_b else a
        keep = a if drop == b else b
        suggestions.append({
            "drop": drop,
            "keep": keep,
            "reason": f"|corr|={abs(p['corr'])}, conservar la de mayor varianza ({keep} var={round(max(var_a, var_b), 4)})",
        })
        drop_set.add(drop)
        keep_set.add(keep)

    for p in categorical_pairs:
        a, b = p["col_a"], p["col_b"]
        if a in drop_set or b in drop_set:
            continue
        # Comparar cardinalidad
        nu_a = df[a].nunique()
        nu_b = df[b].nunique()
        drop = b if nu_a >= nu_b else a
        keep = a if drop == b else b
        suggestions.append({
            "drop": drop,
            "keep": keep,
            "reason": f"Cramér's V={p['cramers_v']}, conservar la de mayor cardinalidad ({keep} con {max(nu_a, nu_b)} valores únicos)",
        })
        drop_set.add(drop)
        keep_set.add(keep)

    return suggestions


# ============================================================
# INTEG-4: DEDUP BY CORRELATION
# ============================================================


@router.get("/dedup_by_correlation/{tabla}")
async def dedup_by_correlation(
    tabla: str,
    threshold: float = Query(0.9, ge=0.5, le=1.0),
) -> dict:
    """
    INTEG-4 — Aplica la decisión de drop sugerida por INTEG-3.

    Devuelve el schema ANTES y DESPUÉS de eliminar las columnas
    redundantes, junto con el listado de columnas eliminadas.

    No modifica el dataset en disco — solo simula la operación y
    devuelve qué cambiaría.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")

    df = load_table(tabla)
    redundancy = await find_redundancy(tabla, threshold)

    drops = [s["drop"] for s in redundancy["drop_candidates"]]
    final_cols = [c for c in df.columns if c not in drops]

    return {
        "table": tabla,
        "threshold": threshold,
        "columns_before": int(len(df.columns)),
        "columns_after": int(len(final_cols)),
        "columns_dropped": drops,
        "columns_kept": final_cols,
        "drop_reasons": redundancy["drop_candidates"],
        "reduction_pct": round(100 * len(drops) / max(1, len(df.columns)), 2),
    }
