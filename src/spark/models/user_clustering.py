"""
Modelo 5: Clustering de Usuarios

Agrupa usuarios por comportamiento usando K-Means.

Features:
  - posts_count, posts_per_day
  - likes_given, likes_received
  - followers_count, following_count
  - avg_likes_per_post
  - days_active

Output: Cada usuario con su cluster asignado + descripción del cluster.
"""

import os
from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import functions as F

from src.config import SPARK_MASTER, GOLD_PATH, IS_LOCAL

MODEL_NAME = "user_clustering"

FEATURE_COLS = [
    "posts_count", "posts_per_day",
    "likes_given", "likes_received",
    "followers_count", "following_count",
    "avg_likes_per_post", "days_active",
]


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


def train(spark: SparkSession = None, input_path: str = None,
          output_path: str = None, k: int = 5):
    """Entrena K-Means y asigna clusters."""
    own_spark = spark is None
    if own_spark:
        spark = get_spark()
        spark.sparkContext.setLogLevel("WARN")

    input_path = input_path or str(GOLD_PATH / "user_stats")
    output_path = output_path or str(GOLD_PATH / "models" / MODEL_NAME)

    print(f"{'='*60}")
    print(f"USER CLUSTERING — Training (k={k})")
    print(f"{'='*60}")

    # Load
    df = spark.read.parquet(input_path)
    df = df.filter(F.col("is_spam") == False).na.fill(0)  # noqa: E712
    print(f"\nUsers: {df.count()}")

    # Pipeline
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features",
                            withStd=True, withMean=True)
    kmeans = KMeans(
        featuresCol="features", predictionCol="cluster",
        k=k, seed=42, maxIter=50,
    )
    pipeline = Pipeline(stages=[assembler, scaler, kmeans])

    # Find optimal k using silhouette
    print("\nEvaluating k values...")
    evaluator = ClusteringEvaluator(featuresCol="features", predictionCol="cluster")
    results = []

    # Precompute assembler + scaler
    pre_pipeline = Pipeline(stages=[assembler, scaler])
    pre_model = pre_pipeline.fit(df)
    scaled_df = pre_model.transform(df)

    for test_k in range(3, 8):
        km = KMeans(featuresCol="features", predictionCol="cluster",
                    k=test_k, seed=42, maxIter=50)
        km_model = km.fit(scaled_df)
        preds = km_model.transform(scaled_df)
        score = evaluator.evaluate(preds)
        results.append((test_k, round(score, 4)))
        print(f"  k={test_k}: silhouette={score:.4f}")

    best_k = max(results, key=lambda x: x[1])[0]
    print(f"\nBest k: {best_k}")

    # Retrain with best k
    kmeans = KMeans(featuresCol="features", predictionCol="cluster",
                    k=best_k, seed=42, maxIter=50)
    final_pipeline = Pipeline(stages=[assembler, scaler, kmeans])
    model = final_pipeline.fit(df)
    clustered = model.transform(df)

    # Cluster profiles
    print(f"\nCluster profiles:")
    profiles = (
        clustered
        .groupBy("cluster")
        .agg(
            F.count("*").alias("size"),
            F.round(F.avg("posts_count"), 1).alias("avg_posts"),
            F.round(F.avg("likes_received"), 1).alias("avg_likes_recv"),
            F.round(F.avg("followers_count"), 1).alias("avg_followers"),
            F.round(F.avg("following_count"), 1).alias("avg_following"),
            F.round(F.avg("posts_per_day"), 2).alias("avg_posts_day"),
        )
        .orderBy("cluster")
    )
    profiles.show()

    # Label clusters based on behavior
    cluster_labels = {}
    for row in profiles.collect():
        c = row["cluster"]
        if row["avg_posts_day"] > 2:
            cluster_labels[c] = "Power User"
        elif row["avg_followers"] > profiles.agg(F.avg("avg_followers")).collect()[0][0] * 1.5:
            cluster_labels[c] = "Influencer"
        elif row["avg_posts"] < 5:
            cluster_labels[c] = "Lurker"
        elif row["avg_likes_recv"] > profiles.agg(F.avg("avg_likes_recv")).collect()[0][0]:
            cluster_labels[c] = "Engaged Creator"
        else:
            cluster_labels[c] = "Regular User"

    print("Cluster labels:")
    for c, label in sorted(cluster_labels.items()):
        print(f"  Cluster {c}: {label}")

    # Save clustered users
    result = clustered.select(
        "_id", "username", "cluster",
        "posts_count", "likes_received", "followers_count",
        "following_count", "posts_per_day",
    )
    result.write.parquet(output_path, mode="overwrite")
    print(f"\nSaved to {output_path}")

    metrics = {
        "model": MODEL_NAME,
        "algorithm": f"KMeans (k={best_k})",
        "best_k": best_k,
        "silhouette_scores": {str(k): s for k, s in results},
        "cluster_labels": cluster_labels,
        "cluster_sizes": {str(row["cluster"]): row["size"]
                          for row in profiles.collect()},
    }

    if own_spark:
        spark.stop()

    return metrics


if __name__ == "__main__":
    train()
