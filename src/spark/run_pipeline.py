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
import os

from pyspark.sql import SparkSession

from src.config import SPARK_MASTER, RAW_PATH, SILVER_PATH, GOLD_PATH, IS_LOCAL


def get_spark(with_connectors: bool = False) -> SparkSession:
    if IS_LOCAL:
        java17 = "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
        if os.path.exists(java17):
            os.environ["JAVA_HOME"] = java17

    builder = (
        SparkSession.builder
        .master(SPARK_MASTER)
        .appName("SocialLab Pipeline")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .config("spark.driver.memory", "2g")
    )

    if with_connectors:
        builder = builder.config(
            "spark.jars.packages",
            "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0,"
            "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3"
        )

    return builder.getOrCreate()


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
        from src.spark.etl_silver import run_silver
        from src.spark.etl_gold import run_gold

        print(f"Raw:    {raw}")
        print(f"Silver: {silver}")
        print(f"Gold:   {gold}\n")

        run_silver(spark, raw, silver)
        print()
        run_gold(spark, silver, gold)
        print()

    if args.all or args.mongo:
        from src.spark.load_to_mongo import (
            load_users, load_posts, load_likes, load_follows,
            load_hashtag_trends, load_user_stats,
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
            clean_neo4j, load_user_nodes, load_hashtag_nodes,
            load_follows_edges, load_interested_in_edges,
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
