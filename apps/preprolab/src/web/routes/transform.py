"""Bloque TRANSFORM — soluciones.

Implementa las técnicas del Tema 5 sobre conversiones y discretización:

  TRANS-1  onehot         Nominal multivaluado → C_v binarias por valor
  TRANS-2  ordinal        Categórica ordenada → numérica con orden custom
  TRANS-3  multivalued    CSV en string → flags binarios (ej. sensores_activos)
  TRANS-4  discretize     Numérica → intervalos (equal-width / equal-freq / mdlp)
  TRANS-5  groupby        Agregación por una columna con varias funciones

MDLP (Fayyad-Irani): el PDF del Tema 5 lo menciona como supervisado.
Implementación interna usa entropía + criterio MDL recursivamente para
encontrar cortes óptimos respecto a la clase. Aquí lo implementamos
mínimamente: si method=mdlp se aplica con target=failure_next_48h por
defecto (sólo disponible para la tabla robots).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/transform", tags=["preprolab-transform"])


# ============================================================
# TRANS-1: One-hot encoding
# ============================================================


@router.get("/onehot/{tabla}/{columna}")
async def onehot(
    tabla: str,
    columna: str,
    max_categories: int = Query(20, ge=2, le=200),
) -> dict:
    """
    TRANS-1 — One-hot encoding.

    Para cada valor único v de la columna, crea una columna binaria
    `<columna>_<v>` con 1 si la fila tiene ese valor, 0 si no.

    Si hay más de `max_categories` valores únicos, agrupamos los menos
    frecuentes en una categoría `OTROS` (técnica del PDF para variables
    con muchos valores tipo "código de estado").
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")

    series = df[columna].astype(str).fillna("(null)")
    counts = series.value_counts()

    grouped = False
    if len(counts) > max_categories:
        top = counts.head(max_categories - 1).index
        series = series.where(series.isin(top), other="OTROS")
        grouped = True

    # One-hot (pd.get_dummies)
    onehot_df = pd.get_dummies(series, prefix=columna, dtype=int)

    # Sample de filas (primeras 5) con las nuevas columnas binarias
    sample = onehot_df.head(5).to_dict("records")

    return {
        "table": tabla,
        "column": columna,
        "n_unique": int(counts.shape[0]),
        "n_categories_kept": int(onehot_df.shape[1]),
        "grouped_minor_into_OTROS": grouped,
        "new_columns": list(onehot_df.columns),
        "distribution": {str(k): int(v) for k, v in counts.head(20).items()},
        "sample": sample,
    }


# ============================================================
# TRANS-2: Ordinal encoding
# ============================================================


@router.get("/ordinal/{tabla}/{columna}")
async def ordinal(
    tabla: str,
    columna: str,
    order: Optional[str] = Query(None, description="CSV con el orden, p.ej. INFO,WARN,ERROR,CRITICAL"),
) -> dict:
    """
    TRANS-2 — Encoding ordinal con orden custom.

    Convierte categorías a enteros respetando un orden lógico.
    Útil para variables como severidad (INFO < WARN < ERROR < CRITICAL)
    o nivel educativo (primaria < secundaria < grado < máster < doctorado).

    Si no se pasa `order`, se infiere del orden alfabético (lo cual es
    casi siempre incorrecto — se devuelve un warning).
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")

    series = df[columna].astype(str).fillna("(null)")
    unique_values = sorted(series.unique().tolist())

    if order:
        provided_order = [v.strip() for v in order.split(",")]
        mapping = {v: i + 1 for i, v in enumerate(provided_order)}
        warning = None
        # Detectar valores en la columna que no están en el order
        missing = set(unique_values) - set(provided_order)
        if missing:
            for m in missing:
                mapping[m] = 0  # marcador
            warning = f"Valores en la columna sin orden especificado (asignado 0): {sorted(missing)}"
    else:
        mapping = {v: i + 1 for i, v in enumerate(unique_values)}
        warning = (
            "No se ha especificado orden — se ha usado orden alfabético. "
            "Esto es casi siempre incorrecto. Especifica `order=v1,v2,v3,...` "
            "con la jerarquía real."
        )

    encoded = series.map(mapping)

    return {
        "table": tabla,
        "column": columna,
        "mapping": {str(k): int(v) for k, v in mapping.items()},
        "n_unique": len(unique_values),
        "stats_encoded": {
            "mean": float(encoded.mean()),
            "median": float(encoded.median()),
            "min": int(encoded.min()),
            "max": int(encoded.max()),
        },
        "value_counts_original": {str(k): int(v) for k, v in series.value_counts().head(20).items()},
        "warning": warning,
        "sample": [
            {"original": str(o), "encoded": int(e)}
            for o, e in list(zip(series.head(5), encoded.head(5)))
        ],
    }


# ============================================================
# TRANS-3: Multivalued (CSV → flags)
# ============================================================


@router.get("/multivalued/{tabla}/{columna}")
async def multivalued(
    tabla: str,
    columna: str,
    separator: str = Query(",", description="Separador del CSV interno"),
) -> dict:
    """
    TRANS-3 — Columna multivaluada (string CSV) → flags binarios.

    Para columnas como `robots.sensores_activos` que contienen varios
    valores separados por coma: parsea, encuentra el conjunto de valores
    posibles y crea una columna binaria por cada uno.

    Es la versión multi-valor del one-hot.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")

    series = df[columna].fillna("").astype(str)

    # Parsear y obtener vocabulario
    all_values: set[str] = set()
    parsed: list[list[str]] = []
    for cell in series:
        items = [v.strip() for v in cell.split(separator) if v.strip()]
        parsed.append(items)
        all_values.update(items)

    vocab = sorted(all_values)

    # Construir matriz de flags
    flags = {f"{columna}_{v}": [int(v in row) for row in parsed] for v in vocab}
    flag_df = pd.DataFrame(flags)

    # Estadísticas: por flag, cuántas filas la tienen activada
    flag_freq = {col: int(flag_df[col].sum()) for col in flag_df.columns}
    flag_pct = {col: round(100 * v / len(df), 2) for col, v in flag_freq.items()}

    # Cardinalidad: cuántos valores por fila (media, max, distribución)
    cardinality = [len(row) for row in parsed]

    return {
        "table": tabla,
        "column": columna,
        "separator": separator,
        "n_rows": int(len(df)),
        "vocabulary": vocab,
        "n_unique_values": len(vocab),
        "flag_columns_created": list(flags.keys()),
        "flag_frequency": flag_freq,
        "flag_pct": flag_pct,
        "cardinality_stats": {
            "mean": round(float(np.mean(cardinality)), 2),
            "median": int(np.median(cardinality)),
            "min": int(min(cardinality)),
            "max": int(max(cardinality)),
        },
        "sample": [
            {"original": str(o), "flags": {k: int(v) for k, v in flag_df.iloc[i].items()}}
            for i, o in enumerate(series.head(3))
        ],
    }


# ============================================================
# TRANS-4: Discretización
# ============================================================


@router.get("/discretize/{tabla}/{columna}")
async def discretize(
    tabla: str,
    columna: str,
    method: str = Query("equal_width", regex="^(equal_width|equal_freq|mdlp)$"),
    bins: int = Query(5, ge=2, le=20),
    target: str = Query("failure_next_48h"),
) -> dict:
    """
    TRANS-4 — Discretización de columna numérica.

    Métodos:
      equal_width: pd.cut(bins=N) — anchos iguales.
      equal_freq:  pd.qcut(q=N)   — cuantiles (~mismo nº de filas por bin).
      mdlp:        Fayyad-Irani (supervisado): busca cortes que maximizan
                   ganancia de información respecto al target y aplica MDL
                   para decidir cuántos. Sólo si la tabla tiene target.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if columna not in df.columns:
        raise HTTPException(404, detail=f"Columna desconocida: {columna}")
    if not pd.api.types.is_numeric_dtype(df[columna]):
        raise HTTPException(400, detail="discretize solo para numéricas")

    series = df[columna].dropna()

    if method == "equal_width":
        bins_result, edges = pd.cut(series, bins=bins, retbins=True, duplicates="drop")
        edges_list = [float(x) for x in edges]
    elif method == "equal_freq":
        bins_result, edges = pd.qcut(series, q=bins, retbins=True, duplicates="drop")
        edges_list = [float(x) for x in edges]
    else:  # mdlp
        if target not in df.columns:
            raise HTTPException(400, detail=f"MDLP requiere target. {target} no existe en {tabla}.")
        edges_list = _mdlp_cuts(series, df.loc[series.index, target])
        if len(edges_list) < 2:
            return {
                "table": tabla, "column": columna, "method": method,
                "warning": "MDLP no encontró cortes útiles — la columna no separa bien la clase.",
                "edges": edges_list,
            }
        bins_result = pd.cut(series, bins=edges_list, include_lowest=True, duplicates="drop")

    # Distribución por bin
    distribution = bins_result.value_counts().sort_index()
    distribution_dict = {str(k): int(v) for k, v in distribution.items()}

    return {
        "table": tabla,
        "column": columna,
        "method": method,
        "n_bins_requested": bins if method != "mdlp" else None,
        "n_bins_resulting": int(len(distribution)),
        "edges": edges_list,
        "distribution": distribution_dict,
    }


def _mdlp_cuts(values: pd.Series, target: pd.Series, max_cuts: int = 8) -> list[float]:
    """Discretización MDLP (Fayyad-Irani) simplificada.

    Busca recursivamente el corte que maximiza ganancia de información y
    aplica criterio MDL para decidir si aceptarlo. Para que sea robusto
    en tiempo, limitamos a `max_cuts` cortes.
    """
    sorted_idx = values.sort_values().index
    sv = values.loc[sorted_idx].values
    st = target.loc[sorted_idx].values.astype(int)

    edges: list[float] = [float(sv.min()), float(sv.max())]

    def _entropy(arr: np.ndarray) -> float:
        if len(arr) == 0:
            return 0.0
        _, counts = np.unique(arr, return_counts=True)
        probs = counts / counts.sum()
        return float(-np.sum(probs * np.log2(probs + 1e-12)))

    def _best_split(values_arr: np.ndarray, target_arr: np.ndarray) -> tuple[float, float] | None:
        n = len(values_arr)
        if n < 4:
            return None
        e_full = _entropy(target_arr)
        best_gain = 0.0
        best_threshold = None
        # Probamos puntos medios entre valores consecutivos distintos
        unique_vals = np.unique(values_arr)
        for i in range(len(unique_vals) - 1):
            t = (unique_vals[i] + unique_vals[i + 1]) / 2.0
            left = target_arr[values_arr <= t]
            right = target_arr[values_arr > t]
            if len(left) == 0 or len(right) == 0:
                continue
            e_left = _entropy(left)
            e_right = _entropy(right)
            e_split = (len(left) / n) * e_left + (len(right) / n) * e_right
            gain = e_full - e_split
            if gain > best_gain:
                best_gain = gain
                best_threshold = t
        if best_threshold is None:
            return None
        return float(best_threshold), best_gain

    # Recursión BFS: encontrar cortes hasta llenar max_cuts
    segments = [(sv, st)]
    cuts: list[float] = []
    while len(cuts) < max_cuts and segments:
        # Buscar el mejor corte en cualquier segmento actual
        candidates = []
        for sv_seg, st_seg in segments:
            cs = _best_split(sv_seg, st_seg)
            if cs is not None:
                candidates.append((cs[1], cs[0], sv_seg, st_seg))
        if not candidates:
            break
        candidates.sort(reverse=True, key=lambda x: x[0])
        gain, t, sv_seg, st_seg = candidates[0]
        # Aplicar criterio MDL simplificado: aceptar si gain > log2(n)/n
        n = len(sv_seg)
        if gain <= np.log2(max(2, n)) / n:
            break
        cuts.append(t)
        # Reemplazar el segmento por sus dos mitades
        new_segments = []
        for sv_s, st_s in segments:
            if sv_s.min() <= t <= sv_s.max() and (sv_s is sv_seg or st_s is st_seg):
                left_mask = sv_s <= t
                new_segments.append((sv_s[left_mask], st_s[left_mask]))
                new_segments.append((sv_s[~left_mask], st_s[~left_mask]))
            else:
                new_segments.append((sv_s, st_s))
        segments = new_segments

    all_edges = sorted(set([float(sv.min())] + cuts + [float(sv.max())]))
    return all_edges


# ============================================================
# TRANS-5: GroupBy + agregaciones
# ============================================================


@router.get("/groupby/{tabla}")
async def groupby(
    tabla: str,
    by: str = Query(..., description="Columna por la que agrupar"),
    agg_col: str = Query(..., description="Columna numérica a agregar"),
    agg: str = Query("mean", regex="^(mean|sum|count|min|max|median|std)$"),
) -> dict:
    """
    TRANS-5 — Agregación con groupby.

    Agrupa por `by` y aplica la función `agg` a `agg_col`. Útil para
    construir features derivadas y/o tablas analíticas.

    Ejemplo: groupby('events', by='tipo', agg_col='robot_id', agg='count')
    → cuenta cuántos events tiene cada tipo.
    """
    if tabla not in TABLES:
        raise HTTPException(404, detail=f"Tabla desconocida: {tabla}")
    df = load_table(tabla)
    if by not in df.columns:
        raise HTTPException(400, detail=f"Columna by={by} no existe")
    if agg_col not in df.columns:
        raise HTTPException(400, detail=f"Columna agg_col={agg_col} no existe")

    if agg == "count":
        grouped = df.groupby(by)[agg_col].count()
    else:
        if not pd.api.types.is_numeric_dtype(df[agg_col]):
            raise HTTPException(400, detail=f"agg={agg} requiere {agg_col} numérica")
        grouped = df.groupby(by)[agg_col].agg(agg)

    result = grouped.sort_values(ascending=False).head(50)

    return {
        "table": tabla,
        "by": by,
        "agg_col": agg_col,
        "agg": agg,
        "n_groups": int(len(grouped)),
        "result": {str(k): (float(v) if pd.notna(v) else None) for k, v in result.items()},
    }
