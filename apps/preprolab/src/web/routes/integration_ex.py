"""Bloque INTEGRATION — scaffolds (versión alumno).

Cuatro ejercicios sobre integración de datos:

  INTEG-1  union              concatenación vertical (mismo schema)
  INTEG-2  join               4 tipos: inner / left / right / outer
  INTEG-3  find_redundancy    Pearson + Cramér's V para detectar redundantes
  INTEG-4  dedup_by_corr      aplica la decisión de drop

Flujo de trabajo:
  1. Implementa las funciones en este archivo.
  2. Ejecuta `./lab.sh preprolab restart` para recargar FastAPI.
  3. Recarga la pestaña Integración en la web.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/integration", tags=["preprolab-integration"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


@router.get("/union/{tabla_a}/{tabla_b}")
async def union(
    tabla_a: str,
    tabla_b: str,
    same_schema_only: bool = Query(True),
) -> dict:
    """
    EJERCICIO INTEG-1 — Concatenación vertical (union) de dos DataFrames.

    Detecta primero si los schemas coinciden. Si SÍ, hace pd.concat() normal.
    Si NO y same_schema_only=False, hace un union "permisivo" sobre columnas
    COMUNES (descartando las que solo están en una de las tablas).

    Estructura esperada:
        {
          "table_a", "table_b",
          "rows_a", "rows_b",
          "schemas_match", "common_columns", "only_in_a", "only_in_b",
          "unioned_rows", "mode",  # strict_union | common_columns_only | blocked
          "warning" | "error_msg"  # según corresponda
        }

    Pistas:
      - cols_a = set(df_a.columns); usar &/-/| para intersección/diferencia/unión.
      - pd.concat([df_a, df_b], ignore_index=True).
      - Para permisivo: pd.concat([df_a[common], df_b[common]], ignore_index=True).
    """
    return _exercise_placeholder(
        "INTEG-1",
        "Implementa union de DataFrames detectando incompatibilidad de schemas.",
    )


@router.get("/join/{tabla_a}/{tabla_b}")
async def join(
    tabla_a: str,
    tabla_b: str,
    on: str = Query(..., description="Columna clave (debe existir en ambas)"),
    how: str = Query("inner", regex="^(inner|left|right|outer)$"),
) -> dict:
    """
    EJERCICIO INTEG-2 — Los 4 tipos de unión SQL.

    Aplica pd.merge(df_a, df_b, on=on, how=how) y devuelve:
      - rows resultantes
      - cardinalidad de la columna clave en cada tabla
      - keys comunes vs solo en una de las dos
      - muestra de 5 filas resultantes

    Estructura esperada:
        {
          "table_a", "table_b", "on", "how",
          "rows_a", "rows_b", "rows_joined",
          "keys_in_a", "keys_in_b", "keys_in_common",
          "keys_only_in_a", "keys_only_in_b",
          "columns_after_join": [...],
          "sample": [...]  # primeras 5 filas (NaN → None para JSON)
        }

    Pistas:
      - Verifica que `on` existe en ambas tablas (400 si no).
      - Usa suffixes=("_a", "_b") para evitar conflictos de columnas.
      - df[on].dropna().unique() para sacar las keys.
      - Para serializar, .replace({np.nan: None}) antes de to_dict.
    """
    return _exercise_placeholder(
        "INTEG-2",
        "Implementa los 4 joins con pd.merge. Reporta cardinalidad de keys "
        "en ambas tablas para que el alumno entienda el efecto del 'how'.",
    )


@router.get("/find_redundancy/{tabla}")
async def find_redundancy(
    tabla: str,
    threshold: float = Query(0.9, ge=0.5, le=1.0),
) -> dict:
    """
    EJERCICIO INTEG-3 — Detecta columnas redundantes.

    Para pares NUMÉRICOS: Pearson PCC; redundantes si |r| > threshold.
    Para pares CATEGÓRICOS: Cramér's V (generalización de Phi); redundantes
    si V > threshold.

    Sugiere también qué columna eliminar de cada par:
      - Numéricas: la de menor varianza (la otra mantiene más info).
      - Categóricas: la de menor cardinalidad.

    Estructura esperada:
        {
          "table", "threshold",
          "numeric_columns_analyzed", "categorical_columns_analyzed",
          "redundant_numeric_pairs": [{"col_a", "col_b", "corr"}, ...],
          "redundant_categorical_pairs": [{"col_a", "col_b", "cramers_v"}, ...],
          "drop_candidates": [{"drop", "keep", "reason"}, ...]
        }

    Cramér's V (sin scipy):
        contingency = pd.crosstab(s1.dropna(), s2.dropna())
        observed = contingency.values
        n = observed.sum()
        row_totals = observed.sum(axis=1, keepdims=True)
        col_totals = observed.sum(axis=0, keepdims=True)
        expected = row_totals @ col_totals / n
        chi2 = np.sum((observed - expected) ** 2 / np.where(expected==0, 1, expected))
        v = np.sqrt(chi2 / (n * min(rows-1, cols-1)))

    Pistas:
      - df[num_cols].corr(method='pearson') devuelve la matriz Pearson.
      - Itera con i < j para evitar duplicados/diagonal.
      - var_a = df[a].var(); más varianza → más poder discriminativo.
    """
    return _exercise_placeholder(
        "INTEG-3",
        "Implementa detección de redundancia con Pearson (numéricas) + "
        "Cramér's V (categóricas). Sugiere drops por varianza/cardinalidad.",
    )


@router.get("/dedup_by_correlation/{tabla}")
async def dedup_by_correlation(
    tabla: str,
    threshold: float = Query(0.9, ge=0.5, le=1.0),
) -> dict:
    """
    EJERCICIO INTEG-4 — Aplica el dedup sugerido por INTEG-3.

    Llama internamente a find_redundancy(tabla, threshold), extrae la
    lista de drops y devuelve schema antes/después.

    Estructura esperada:
        {
          "table", "threshold",
          "columns_before", "columns_after",
          "columns_dropped": [...], "columns_kept": [...],
          "drop_reasons": [...],
          "reduction_pct": float
        }

    No modifica el dataset en disco — solo simula la operación.
    """
    return _exercise_placeholder(
        "INTEG-4",
        "Llama a find_redundancy y devuelve el schema con las columnas "
        "redundantes eliminadas. No modifica el dataset.",
    )
