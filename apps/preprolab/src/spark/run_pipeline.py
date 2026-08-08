"""Pipeline Spark de PreproLab: Raw → Silver.

Uso (dentro del contenedor o en local con Java 17):

    python -m src.spark.run_pipeline

Ingesta las 4 tablas de la flota de robots a la capa silver (parquet),
preservando la suciedad inyectada —es el material de los ejercicios del
Tema 5— y generando un perfil de calidad con agregaciones Spark.

Los bloques de preprocesamiento (missing, outliers, transform…) siguen
corriendo en pandas/sklearn sobre esta capa silver: parquet columnar se
lee mucho más rápido que el JSON crudo y la UI mantiene su interactividad.
"""

from __future__ import annotations

from infra.shared.spark import build_spark
from src.config import RAW_PATH, SILVER_PATH
from src.spark.etl_silver import run_silver


def main() -> None:
    spark = build_spark("PreproLab ETL")
    spark.sparkContext.setLogLevel("WARN")

    print(f"Raw:    {RAW_PATH}")
    print(f"Silver: {SILVER_PATH}\n")

    if not RAW_PATH.exists() or not any(RAW_PATH.glob("*.json")):
        raise SystemExit(
            f"No hay datos raw en {RAW_PATH}. Ejecuta antes `./lab.sh preprolab seed`."
        )

    run_silver(spark, str(RAW_PATH), str(SILVER_PATH))
    spark.stop()
    print("\n[OK] Capa silver lista. Los endpoints ya leen parquet.")


if __name__ == "__main__":
    main()
