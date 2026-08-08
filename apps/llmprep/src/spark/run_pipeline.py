"""Pipeline Spark de LLM Lab: Raw → Silver.

Uso (dentro del contenedor o en local con Java 17):

    python -m src.spark.run_pipeline

Ingesta el corpus crudo a la capa silver (parquet), preservando la suciedad
—es el material de los bloques clean/dedup/tokenize— y generando el perfil de
ruido (ground truth) con agregaciones Spark.

Los bloques de limpieza siguen corriendo sobre esta capa silver: parquet
columnar se lee más rápido que el JSON crudo en cada arranque del contenedor.
"""

from __future__ import annotations

from infra.shared.spark import build_spark
from src.config import RAW_PATH, SILVER_PATH
from src.spark.etl_silver import run_silver


def main() -> None:
    spark = build_spark("LLM Lab ETL")
    spark.sparkContext.setLogLevel("WARN")

    print(f"Raw:    {RAW_PATH}")
    print(f"Silver: {SILVER_PATH}\n")

    if not (RAW_PATH / "corpus.json").exists():
        raise SystemExit(
            f"No hay corpus en {RAW_PATH}. Ejecuta antes `./lab.sh llmprep ingest`."
        )

    run_silver(spark, str(RAW_PATH), str(SILVER_PATH))
    spark.stop()
    print("\n[OK] Capa silver lista. Los endpoints ya leen parquet.")


if __name__ == "__main__":
    main()
