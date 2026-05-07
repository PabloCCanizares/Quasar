"""
Modelo 6: Predicción de Churn

¿Este usuario va a dejar de publicar?

Define churn como: usuario que no ha publicado en los últimos N días
del periodo de datos.

Features:
  - posts_count, posts_per_day
  - days_since_last_post
  - trend_posts (posts recientes vs antiguos)
  - likes_received, likes_given
  - followers_count, following_count
  - engagement_trend (likes recientes vs antiguos)

Label: is_churned (0/1)

Modelo: GBTClassifier.
"""

import os
from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import functions as F
from pyspark.sql import Window

from src.config import SPARK_MASTER, SILVER_PATH, GOLD_PATH, IS_LOCAL

MODEL_NAME = "churn_predictor"

CHURN_DAYS = 30  # Sin actividad en los últimos 30 días = churn

FEATURE_COLS = [
    "posts_count", "posts_per_day",
    "days_since_last_post",
    "recent_posts_ratio",
    "likes_received", "likes_given",
    "followers_count", "following_count",
    "recent_likes_ratio",
    "days_active",
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


def build_features(spark: SparkSession, silver_path: str, gold_path: str):
    """Construye features de churn."""
    posts = spark.read.parquet(f"{silver_path}/posts")
    likes = spark.read.parquet(f"{silver_path}/likes")
    user_stats = spark.read.parquet(f"{gold_path}/user_stats")

    # Reference date (max date in posts)
    max_date = posts.agg(F.max("created_at")).collect()[0][0]
    midpoint = posts.agg(
        F.expr("percentile_approx(unix_timestamp(created_at), 0.5)")
    ).collect()[0][0]

    # Posts features per user
    post_features = posts.groupBy("user_id").agg(
        F.count("*").alias("posts_count"),
        F.max("created_at").alias("last_post_at"),
        # Recent vs old posts
        F.sum(F.when(F.unix_timestamp("created_at") > midpoint, 1).otherwise(0)).alias("recent_posts"),
        F.sum(F.when(F.unix_timestamp("created_at") <= midpoint, 1).otherwise(0)).alias("old_posts"),
    )

    post_features = (
        post_features
        .withColumn("days_since_last_post",
                     F.datediff(F.lit(max_date), F.col("last_post_at")))
        .withColumn("recent_posts_ratio",
                     F.when(F.col("posts_count") > 0,
                            F.col("recent_posts") / F.col("posts_count"))
                     .otherwise(0))
        .drop("last_post_at", "recent_posts", "old_posts")
    )

    # Likes features
    post_user = posts.select(F.col("_id").alias("pid"), F.col("user_id").alias("post_author"))
    likes_with_author = likes.join(post_user, likes.post_id == post_user.pid, "inner")

    likes_given = likes.groupBy("user_id").agg(F.count("*").alias("likes_given"))
    likes_received = (
        likes_with_author
        .groupBy("post_author")
        .agg(
            F.count("*").alias("likes_received"),
            F.sum(F.when(F.unix_timestamp(likes.created_at) > midpoint, 1).otherwise(0))
            .alias("recent_likes"),
            F.count("*").alias("total_likes"),
        )
        .withColumn("recent_likes_ratio",
                     F.when(F.col("total_likes") > 0,
                            F.col("recent_likes") / F.col("total_likes"))
                     .otherwise(0))
        .select(F.col("post_author").alias("author_id"),
                "likes_received", "recent_likes_ratio")
    )

    # Base from user_stats
    base = user_stats.select(
        "_id", "username", "is_spam",
        "followers_count", "following_count",
        "posts_per_day", "days_active",
    ).filter(F.col("is_spam") == False)  # noqa: E712

    # Join all
    df = (
        base
        .join(post_features, base._id == post_features.user_id, "left").drop("user_id")
        .join(likes_given, base._id == likes_given.user_id, "left").drop("user_id")
        .join(likes_received, base._id == likes_received.author_id, "left").drop("author_id")
        .na.fill(0)
    )

    # Label: churned if no posts in last CHURN_DAYS days
    df = df.withColumn(
        "label",
        F.when(F.col("days_since_last_post") >= CHURN_DAYS, 1.0).otherwise(0.0)
    )

    return df


def train(spark: SparkSession = None, silver_path: str = None,
          gold_path: str = None, output_path: str = None):
    """Entrena el predictor de churn."""
    own_spark = spark is None
    if own_spark:
        spark = get_spark()
        spark.sparkContext.setLogLevel("WARN")

    silver_path = silver_path or str(SILVER_PATH)
    gold_path = gold_path or str(GOLD_PATH)
    output_path = output_path or str(GOLD_PATH / "models" / MODEL_NAME)

    print(f"{'='*60}")
    print(f"CHURN PREDICTOR — Training")
    print(f"{'='*60}")

    df = build_features(spark, silver_path, gold_path)
    print(f"\nDataset: {df.count()} users")
    print("Class distribution:")
    df.groupBy("label").count().show()

    # Split
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

    # Pipeline
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features",
                            withStd=True, withMean=True)
    gbt = GBTClassifier(
        labelCol="label", featuresCol="features",
        maxIter=50, maxDepth=6, seed=42,
    )
    pipeline = Pipeline(stages=[assembler, scaler, gbt])

    print("\nTraining GBTClassifier...")
    model = pipeline.fit(train_df)
    predictions = model.transform(test_df)

    # Evaluate
    auc_eval = BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC")
    mc_eval = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")

    metrics = {
        "model": MODEL_NAME,
        "algorithm": "GBTClassifier",
        "churn_threshold_days": CHURN_DAYS,
        "auc": round(auc_eval.evaluate(predictions), 4),
        "accuracy": round(mc_eval.evaluate(predictions, {mc_eval.metricName: "accuracy"}), 4),
        "precision": round(mc_eval.evaluate(predictions, {mc_eval.metricName: "weightedPrecision"}), 4),
        "recall": round(mc_eval.evaluate(predictions, {mc_eval.metricName: "weightedRecall"}), 4),
        "f1": round(mc_eval.evaluate(predictions, {mc_eval.metricName: "f1"}), 4),
        "train_size": train_df.count(),
        "test_size": test_df.count(),
    }

    print(f"\nResults:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Feature importance
    gbt_model = model.stages[-1]
    importances = list(zip(FEATURE_COLS, gbt_model.featureImportances.toArray()))
    importances.sort(key=lambda x: x[1], reverse=True)
    print(f"\nFeature Importance:")
    for feat, imp in importances:
        print(f"  {feat}: {imp:.4f}")

    metrics["feature_importance"] = {f: round(float(v), 4) for f, v in importances}

    # Save
    model.write().overwrite().save(output_path)
    predictions.select("_id", "username", "label", "prediction", "probability") \
        .write.parquet(f"{output_path}_predictions", mode="overwrite")

    print(f"\nModel saved to {output_path}")

    if own_spark:
        spark.stop()

    return metrics


if __name__ == "__main__":
    train()
