"""
Ejecuta el pipeline completo:
  1. Raw → Silver (limpieza)
  2. Silver → Gold (agregados)
  3. Silver/Gold → MongoDB (carga app)
  4. MongoDB → Neo4j (grafo social)

Uso local:
    python -m src.spark.run_pipeline          # Solo ETL (raw→silver→gold)
    python -m src.spark.run_pipeline --all     # ETL + carga MongoDB + Neo4j
    python -m src.spark.run_pipeline --mongo   # Solo carga a MongoDB
    python -m src.spark.run_pipeline --neo4j   # Solo carga a Neo4j

En Databricks:
    Ejecutar los módulos por separado con rutas ajustadas.
"""

import argparse

from pyspark.sql import SparkSession

from infra.shared.spark import build_spark
from src.config import GOLD_PATH, RAW_PATH, SILVER_PATH


def get_spark(with_connectors: bool = False) -> SparkSession:
    """Compatibilidad: delega en infra.shared.spark.build_spark."""
    return build_spark("SocialLab Pipeline", with_connectors=with_connectors)


def main():
    parser = argparse.ArgumentParser(description="SocialLab Spark Pipeline")
    parser.add_argument("--all", action="store_true", help="Run ETL + load MongoDB + Neo4j")
    parser.add_argument("--mongo", action="store_true", help="Load silver/gold to MongoDB")
    parser.add_argument("--neo4j", action="store_true", help="Load graph to Neo4j")
    args = parser.parse_args()

    run_etl = not args.mongo and not args.neo4j  # ETL by default unless only loading
    needs_connectors = args.all or args.mongo or args.neo4j

    spark = get_spark(with_connectors=needs_connectors)
    spark.sparkContext.setLogLevel("WARN")

    raw = str(RAW_PATH)
    silver = str(SILVER_PATH)
    gold = str(GOLD_PATH)

    if run_etl or args.all:
        from src.spark.etl_gold import run_gold
        from src.spark.etl_silver import run_silver

        print(f"Raw:    {raw}")
        print(f"Silver: {silver}")
        print(f"Gold:   {gold}\n")

        run_silver(spark, raw, silver)
        print()
        run_gold(spark, silver, gold)
        print()

    if args.all or args.mongo:
        from src.spark.load_to_mongo import (
            load_follows,
            load_hashtag_trends,
            load_likes,
            load_posts,
            load_user_stats,
            load_users,
        )
        print("=" * 50)
        print("SPARK → MONGODB")
        print("=" * 50)
        load_users(spark, silver)
        load_posts(spark, silver)
        load_likes(spark, silver)
        load_follows(spark, silver)
        load_hashtag_trends(spark, gold)
        load_user_stats(spark, gold)
        print()

    if args.all or args.neo4j:
        from src.spark.load_to_neo4j import (
            clean_neo4j,
            load_follows_edges,
            load_hashtag_nodes,
            load_interested_in_edges,
            load_user_nodes,
        )
        print("=" * 50)
        print("SPARK → NEO4J")
        print("=" * 50)
        clean_neo4j(spark)
        load_user_nodes(spark)
        load_hashtag_nodes(spark)
        load_follows_edges(spark)
        load_interested_in_edges(spark)
        print()

    spark.stop()
    print("Pipeline complete!")


if __name__ == "__main__":
    main()
