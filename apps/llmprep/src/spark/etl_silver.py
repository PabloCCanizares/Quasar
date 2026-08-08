"""Spark ETL — Raw → Silver (LLM Lab).

Ingesta el corpus crudo (JSON Lines, ~5450 docs tipo Wikipedia ES) a parquet
columnar en la capa silver.

IMPORTANTE — por qué esta capa NO limpia el corpus:
    Igual que en PreproLab, la suciedad (mojibake, HTML/wikitext, PII, docs en
    otro idioma, longitudes extremas) ES el material de los bloques
    clean / dedup / tokenize. El alumno la trata; el ETL solo ingesta.

    Lo que Spark aporta aquí —trabajo real distribuido—:
      - Ingesta a parquet columnar → lectura rápida en los endpoints.
      - Perfil de la verdad-terreno (`_noise`) por tipo de ruido, vía
        `explode` + `groupBy`: cuántos docs traen encoding roto, HTML, PII,
        idioma erróneo… Es exactamente la distribución que los bloques de
        limpieza deben recuperar, y sirve de referencia para medir precision
        y recall del alumno.

El mismo código corre en local y en Databricks (rutas por parámetro).
"""

from __future__ import annotations

import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def noise_profile(df: DataFrame) -> dict:
    """Distribución de tipos de ruido (ground truth) vía explode + groupBy."""
    total = df.count()
    out: dict = {"docs": total, "clean_docs": 0, "noise_types": {}}
    if "_noise" in df.columns:
        # explode_outer conserva los docs sin ruido como fila nula → clean_docs.
        exploded = df.select(F.explode_outer(F.col("_noise")).alias("noise"))
        rows = exploded.groupBy("noise").count().orderBy(F.desc("count")).collect()
        for row in rows:
            if row["noise"] is None:
                out["clean_docs"] = int(row["count"])
            else:
                out["noise_types"][row["noise"]] = int(row["count"])
    return out


def run_silver(spark: SparkSession, raw_dir: str, silver_dir: str) -> dict:
    """Ingesta el corpus raw → parquet silver, preservando la suciedad.

    Args:
        spark: sesión activa.
        raw_dir: carpeta con `corpus.json` (JSON Lines) del ingest.
        silver_dir: destino; el corpus se escribe en `silver/corpus/`.

    Returns:
        Perfil de ruido (también escrito en `silver/_profile.json`).
    """
    raw = Path(raw_dir)
    silver = Path(silver_dir)

    src = str(raw / "corpus.json")
    # JSON Lines con esquema inferido. Todo se preserva: `text` sucio,
    # `_noise` (array de etiquetas), `lang_declared`, `char_count`…
    df = spark.read.json(src)
    dst = str(silver / "corpus")
    df.write.mode("overwrite").parquet(dst)

    prof = noise_profile(df)
    print(f"[silver] corpus: {prof['docs']} docs ({prof['clean_docs']} limpios) → {dst}")
    for ntype, n in prof["noise_types"].items():
        print(f"[silver]   ruido '{ntype}': {n} docs")

    silver.mkdir(parents=True, exist_ok=True)
    prof_path = silver / "_profile.json"
    prof_path.write_text(json.dumps(prof, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[silver] perfil de ruido → {prof_path}")

    return prof
