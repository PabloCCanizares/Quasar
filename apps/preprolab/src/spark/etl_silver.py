"""Spark ETL — Raw → Silver (PreproLab).

Ingesta la flota de robots del data lake: 4 tablas JSON Lines → parquet
tipado y columnar en la capa silver.

IMPORTANTE — por qué esta capa NO limpia los datos:
    PreproLab es un laboratorio de preprocesamiento. La suciedad inyectada
    por el seed (nulls MCAR/MAR/MNAR, outliers, class noise, encoding roto,
    fechas en 5 formatos, multivaluadas, redundancia entre atributos, PII…)
    ES el material del ejercicio: el alumno la detecta y la corrige en los
    bloques del Tema 5. Si la limpiáramos aquí, no quedaría nada que enseñar.

    Lo que Spark SÍ aporta en esta capa —y es trabajo real distribuido—:
      - Ingesta a escala: lee JSON Lines e infiere/aplica esquema.
      - Formato columnar parquet: los endpoints leen mucho más rápido que
        re-parseando el JSON crudo en cada arranque del contenedor.
      - Perfil de calidad (filas, nulls y dtype por columna) calculado con
        agregaciones Spark en una sola pasada → sidecar `_profile.json` que
        la UI puede mostrar como "radiografía" del dataset antes de limpiarlo.

El mismo código corre en local y en Databricks (las rutas van por parámetro).
"""

from __future__ import annotations

import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# Las 4 tablas de la flota. El orden importa para el log.
TABLES = ["robots", "sensors_readings", "events", "maintenances"]


def quality_profile(df: DataFrame) -> dict:
    """Perfil de calidad por columna vía agregaciones Spark (una pasada).

    Devuelve {"rows": N, "columns": {col: {dtype, nulls, null_pct}}}.
    No altera el DataFrame ni "resuelve" ningún ejercicio: solo mide.
    """
    total = df.count()
    dtypes = dict(df.dtypes)
    columns: dict[str, dict] = {}
    if df.columns:
        null_exprs = [F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in df.columns]
        nulls = df.select(null_exprs).first().asDict()
        for c in df.columns:
            n_null = int(nulls.get(c) or 0)
            columns[c] = {
                "dtype": dtypes.get(c, "unknown"),
                "nulls": n_null,
                "null_pct": round(100.0 * n_null / total, 2) if total else 0.0,
            }
    return {"rows": total, "columns": columns}


def run_silver(spark: SparkSession, raw_dir: str, silver_dir: str) -> dict:
    """Ingesta las 4 tablas raw → parquet silver, preservando la suciedad.

    Args:
        spark: sesión activa.
        raw_dir: carpeta con los `<tabla>.json` (JSON Lines) del seed.
        silver_dir: carpeta destino; cada tabla se escribe en `silver/<tabla>/`.

    Returns:
        Perfil de calidad agregado (también escrito en `silver/_profile.json`).
    """
    raw = Path(raw_dir)
    silver = Path(silver_dir)
    profile: dict[str, dict] = {}

    for table in TABLES:
        src = str(raw / f"{table}.json")
        # JSON Lines con esquema inferido. Los valores sucios se preservan
        # tal cual: strings heterogéneos (fechas en 5 formatos), nulls,
        # outliers numéricos, CSV multivaluado… todo queda como está.
        df = spark.read.json(src)
        dst = str(silver / table)
        df.write.mode("overwrite").parquet(dst)

        prof = quality_profile(df)
        profile[table] = prof
        print(f"[silver] {table}: {prof['rows']} filas, {len(prof['columns'])} cols → {dst}")

    # Sidecar de perfil (dict pequeño; escritura desde el driver).
    silver.mkdir(parents=True, exist_ok=True)
    prof_path = silver / "_profile.json"
    prof_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[silver] perfil de calidad → {prof_path}")

    return profile
