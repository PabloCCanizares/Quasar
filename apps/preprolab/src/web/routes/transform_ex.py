"""Bloque TRANSFORM — scaffolds (versión alumno).

Cinco ejercicios sobre conversiones, discretización y agregaciones del Tema 5:

  TRANS-1  onehot         Nominal → C_v binarias por valor
  TRANS-2  ordinal        Categórica ordenada → numérica con orden custom
  TRANS-3  multivalued    CSV en string → flags binarios
  TRANS-4  discretize     Numérica → intervalos (equal-width / equal-freq / mdlp)
  TRANS-5  groupby        Agregación con varias funciones

Flujo:
  1. Implementa las funciones aquí.
  2. ./lab.sh preprolab restart
  3. Recarga la pestaña Transformación.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/transform", tags=["preprolab-transform"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


@router.get("/onehot/{tabla}/{columna}")
async def onehot(
    tabla: str,
    columna: str,
    max_categories: int = Query(20, ge=2, le=200),
) -> dict:
    """
    EJERCICIO TRANS-1 — One-hot encoding.

    Para cada valor único v de la columna, crea una columna `<columna>_<v>`
    con 0 o 1. Si hay más de `max_categories` valores únicos, los menos
    frecuentes se agrupan en una categoría "OTROS" (técnica del PDF).

    Estructura esperada:
        {
          "table", "column",
          "n_unique", "n_categories_kept",
          "grouped_minor_into_OTROS": bool,
          "new_columns": [...],
          "distribution": {valor: count},  # top 20
          "sample": [...]  # primeras 5 filas con flags binarios
        }

    Pistas:
      - series.value_counts() para ordenar.
      - `series.where(series.isin(top), other="OTROS")` para agrupar.
      - pd.get_dummies(series, prefix=columna, dtype=int).
    """
    return _exercise_placeholder(
        "TRANS-1",
        "Implementa one-hot con pd.get_dummies + agrupación de categorías "
        "minoritarias en OTROS cuando hay > max_categories valores.",
    )


@router.get("/ordinal/{tabla}/{columna}")
async def ordinal(
    tabla: str,
    columna: str,
    order: Optional[str] = Query(None, description="CSV con el orden, ej INFO,WARN,ERROR,CRITICAL"),
) -> dict:
    """
    EJERCICIO TRANS-2 — Encoding ordinal con orden custom.

    Convierte categorías a enteros respetando un orden lógico (no alfabético).
    Si no se pasa `order`, asigna orden alfabético + warning.

    Estructura esperada:
        {
          "table", "column",
          "mapping": {valor: int},
          "n_unique",
          "stats_encoded": {"mean", "median", "min", "max"},
          "value_counts_original": {valor: count},
          "warning": str | null,
          "sample": [{"original", "encoded"}, ...]  # 5 filas
        }

    Pistas:
      - mapping = {v: i+1 for i, v in enumerate(order_list)}.
      - series.map(mapping) para encodear.
      - Detectar valores en la columna que NO están en el order (asignar 0).
    """
    return _exercise_placeholder(
        "TRANS-2",
        "Implementa ordinal encoding con orden custom. Detecta y avisa "
        "si hay valores fuera del orden proporcionado.",
    )


@router.get("/multivalued/{tabla}/{columna}")
async def multivalued(
    tabla: str,
    columna: str,
    separator: str = Query(",", description="Separador del CSV"),
) -> dict:
    """
    EJERCICIO TRANS-3 — Columna multivaluada (CSV) → flags binarios.

    Para una columna como `robots.sensores_activos` que contiene
    "lidar_2d, imu, camera_rgb" en cada celda, descompone en flags
    binarios: una columna por cada valor del vocabulario.

    Estructura esperada:
        {
          "table", "column", "separator", "n_rows",
          "vocabulary": [...],
          "n_unique_values": int,
          "flag_columns_created": [...],
          "flag_frequency": {col: count},
          "flag_pct": {col: pct},
          "cardinality_stats": {"mean", "median", "min", "max"},
          "sample": [{"original", "flags": {col: 0|1}}, ...]
        }

    Pistas:
      - Para cada celda: parts = [v.strip() for v in cell.split(separator) if v.strip()].
      - vocab = sorted({union de todos los parts}).
      - Para crear flags: int(v in row) por cada v del vocab.
      - cardinality = nº de items por fila (lista de longitudes).
    """
    return _exercise_placeholder(
        "TRANS-3",
        "Parsea CSV interno, construye vocabulario, crea flags binarios "
        "por cada valor del vocab.",
    )


@router.get("/discretize/{tabla}/{columna}")
async def discretize(
    tabla: str,
    columna: str,
    method: str = Query("equal_width", regex="^(equal_width|equal_freq|mdlp)$"),
    bins: int = Query(5, ge=2, le=20),
    target: str = Query("failure_next_48h"),
) -> dict:
    """
    EJERCICIO TRANS-4 — Discretización numérica.

    Métodos:
      equal_width: anchos iguales (pd.cut(bins=N)).
      equal_freq:  cuantiles (pd.qcut(q=N)).
      mdlp:        Fayyad-Irani (supervisado). Encuentra cortes que
                    maximizan ganancia de información respecto al target.
                    Sólo si la tabla tiene target.

    Estructura esperada:
        {
          "table", "column", "method",
          "n_bins_requested", "n_bins_resulting",
          "edges": [...],  # bordes de los intervalos
          "distribution": {"intervalo": count}
        }

    Pistas:
      - pd.cut(series, bins=N, retbins=True, duplicates="drop") devuelve
        (Series con intervalos, array de edges).
      - pd.qcut(series, q=N, ...) igual pero por cuantiles.
      - MDLP: recursivamente, en cada segmento buscar el split que
        maximiza la ganancia de información (entropía total - entropía
        ponderada por mitad). Aplicar criterio MDL para parar.
    """
    return _exercise_placeholder(
        "TRANS-4",
        "Implementa equal_width (pd.cut), equal_freq (pd.qcut) y MDLP "
        "(entropy-based, recursivo con criterio MDL).",
    )


@router.get("/groupby/{tabla}")
async def groupby(
    tabla: str,
    by: str = Query(..., description="Columna por la que agrupar"),
    agg_col: str = Query(..., description="Columna a agregar"),
    agg: str = Query("mean", regex="^(mean|sum|count|min|max|median|std)$"),
) -> dict:
    """
    EJERCICIO TRANS-5 — Agregación con groupby.

    Agrupa por `by` y aplica la función `agg` a `agg_col`. Devuelve los
    50 grupos con mayor valor.

    Estructura esperada:
        {
          "table", "by", "agg_col", "agg",
          "n_groups", "result": {grupo: valor}
        }

    Pistas:
      - df.groupby(by)[agg_col].count() para 'count' (funciona con cualquier dtype).
      - df.groupby(by)[agg_col].agg(agg) para mean/sum/min/max/median/std
        (requiere numérica).
      - sort_values(ascending=False).head(50) para top 50.
    """
    return _exercise_placeholder(
        "TRANS-5",
        "Implementa groupby + agg. Recuerda que count funciona con cualquier "
        "dtype, pero mean/sum/etc requieren numérica.",
    )
