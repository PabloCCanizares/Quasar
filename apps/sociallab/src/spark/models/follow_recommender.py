"""
Modelo 4: Recomendación de Follows

¿A quién debería seguir este usuario?

Basado en:
  - Hashtags compartidos (intereses similares)
  - Follows en común (amigos de amigos)
  - Comunidad similar

Genera un score de afinidad entre pares de usuarios.
No es un modelo ML clásico — es un sistema de scoring
que combina señales del grafo y del contenido.

Output: DataFrame con (user_id, recommended_id, score, reason)
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window

from src.config import SPARK_MASTER, SILVER_PATH, GOLD_PATH, IS_LOCAL

MODEL_NAME = "follow_recommender"


def get_spark():
    if IS_LOCAL:
        java17 = "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
        if os.path.exists(java17):
            os.environ["JAVA_HOME"] = java17
    return (
        SparkSession.builder
        .master(SPARK_MASTER)
        .appName(f"SocialLab - {MODEL_NAME}")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def build_recommendations(spark: SparkSession = None, silver_path: str = None,
                           gold_path: str = None, output_path: str = None):
    """Genera recomendaciones de follow para cada usuario."""
    own_spark = spark is None
    if own_spark:
        spark = get_spark()
        spark.sparkContext.setLogLevel("WARN")

    silver_path = silver_path or str(SILVER_PATH)
    gold_path = gold_path or str(GOLD_PATH)
    output_path = output_path or str(GOLD_PATH / "models" / MODEL_NAME)

    print(f"{'='*60}")
    print(f"FOLLOW RECOMMENDER — Building")
    print(f"{'='*60}")

    posts = spark.read.parquet(f"{silver_path}/posts")
    follows = spark.read.parquet(f"{silver_path}/follows")
    users = spark.read.parquet(f"{silver_path}/users")

    # --- Signal 1: Shared hashtags ---
    print("\nCalculating shared hashtag scores...")
    user_hashtags = (
        posts
        .filter(F.col("is_spam") == False)  # noqa: E712
        .withColumn("hashtag", F.explode(F.col("hashtags")))
        .select("user_id", "hashtag")
        .distinct()
    )

    shared_tags = (
        user_hashtags.alias("a")
        .join(user_hashtags.alias("b"),
              (F.col("a.hashtag") == F.col("b.hashtag")) &
              (F.col("a.user_id") < F.col("b.user_id")))
        .groupBy(
            F.col("a.user_id").alias("user_a"),
            F.col("b.user_id").alias("user_b"))
        .agg(F.count("*").alias("shared_tags"))
    )

    # Normalize: score = shared_tags / max_shared_tags
    max_shared = shared_tags.agg(F.max("shared_tags")).collect()[0][0] or 1
    shared_score = shared_tags.withColumn(
        "hashtag_score", F.col("shared_tags") / F.lit(max_shared)
    )

    # --- Signal 2: Friends of friends ---
    print("Calculating friends-of-friends scores...")
    # A follows B, B follows C → recommend C to A
    fof = (
        follows.alias("ab")
        .join(follows.alias("bc"),
              F.col("ab.following_id") == F.col("bc.follower_id"))
        .filter(F.col("ab.follower_id") != F.col("bc.following_id"))
        .groupBy(
            F.col("ab.follower_id").alias("user_a"),
            F.col("bc.following_id").alias("user_b"))
        .agg(F.count("*").alias("mutual_friends"))
    )

    max_fof = fof.agg(F.max("mutual_friends")).collect()[0][0] or 1
    fof_score = fof.withColumn(
        "fof_score", F.col("mutual_friends") / F.lit(max_fof)
    )

    # --- Combine signals ---
    print("Combining signals...")

    # Full outer join both signals
    combined = (
        shared_score.select("user_a", "user_b", "hashtag_score")
        .join(
            fof_score.select("user_a", "user_b", "fof_score"),
            ["user_a", "user_b"],
            "outer"
        )
        .na.fill(0)
    )

    # Final score: weighted combination
    combined = combined.withColumn(
        "score",
        F.col("hashtag_score") * 0.6 + F.col("fof_score") * 0.4
    )

    # Remove pairs that already follow each other
    existing = follows.select(
        F.col("follower_id").alias("e_a"),
        F.col("following_id").alias("e_b"),
    )

    recommendations = (
        combined
        .join(existing,
              (combined.user_a == existing.e_a) & (combined.user_b == existing.e_b),
              "left_anti")
    )

    # Make bidirectional (A→B and B→A)
    recs_ab = recommendations.select(
        F.col("user_a").alias("user_id"),
        F.col("user_b").alias("recommended_id"),
        "score", "hashtag_score", "fof_score",
    )
    recs_ba = recommendations.select(
        F.col("user_b").alias("user_id"),
        F.col("user_a").alias("recommended_id"),
        "score", "hashtag_score", "fof_score",
    )
    all_recs = recs_ab.unionAll(recs_ba)

    # Keep top 10 per user
    window = Window.partitionBy("user_id").orderBy(F.col("score").desc())
    top_recs = (
        all_recs
        .withColumn("rank", F.row_number().over(window))
        .filter(F.col("rank") <= 10)
        .drop("rank")
    )

    # Add reason
    top_recs = top_recs.withColumn(
        "reason",
        F.when(
            (F.col("hashtag_score") > 0) & (F.col("fof_score") > 0),
            F.lit("Intereses comunes + amigos en común")
        ).when(
            F.col("hashtag_score") > 0,
            F.lit("Intereses similares")
        ).otherwise(
            F.lit("Amigos en común")
        )
    )

    # Save
    top_recs.write.parquet(output_path, mode="overwrite")
    total = top_recs.count()
    users_with_recs = top_recs.select("user_id").distinct().count()
    print(f"\n{total} recommendations for {users_with_recs} users")
    print(f"Saved to {output_path}")

    # Sample
    print("\nSample recommendations:")
    top_recs.orderBy(F.col("score").desc()).show(10, truncate=False)

    metrics = {
        "model": MODEL_NAME,
        "algorithm": "Hybrid (hashtags + friends-of-friends)",
        "total_recommendations": total,
        "users_with_recommendations": users_with_recs,
        "avg_score": round(float(top_recs.agg(F.avg("score")).collect()[0][0]), 4),
    }

    if own_spark:
        spark.stop()

    return metrics


if __name__ == "__main__":
    build_recommendations()
