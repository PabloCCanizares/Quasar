"""
Modelo 2: Predicción de Engagement

Predice cuántos likes va a recibir un post (regresión).

Features:
  - num_hashtags, text_length
  - hour_of_day, day_of_week
  - author_followers, author_posts_count
  - author_avg_likes, author_days_active

Label: likes_count (continuo)

Modelo: GBTRegressor.
"""

from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import functions as F

from src.config import SILVER_PATH, GOLD_PATH
from infra.shared.spark import build_spark

MODEL_NAME = "engagement_predictor"

FEATURE_COLS = [
    "num_hashtags", "text_length",
    "hour_of_day", "day_of_week",
    "author_followers", "author_posts_count",
    "author_avg_likes", "author_days_active",
]


def get_spark():
    return build_spark(f"SocialLab - {MODEL_NAME}")


def build_features(spark: SparkSession, silver_path: str, gold_path: str):
    """Construye el dataset de features para engagement."""
    posts = spark.read.parquet(f"{silver_path}/posts")
    likes = spark.read.parquet(f"{silver_path}/likes")
    user_stats = spark.read.parquet(f"{gold_path}/user_stats")

    # Real likes per post
    real_likes = likes.groupBy("post_id").agg(F.count("*").alias("real_likes"))

    # Post features
    df = (
        posts
        .filter(F.col("is_spam") == False)  # noqa: E712
        .withColumn("num_hashtags", F.size(F.col("hashtags")))
        .withColumn("text_length", F.length(F.col("text")))
        .withColumn("hour_of_day", F.hour(F.col("created_at")))
        .withColumn("day_of_week", F.dayofweek(F.col("created_at")))
    )

    # Join real likes
    df = (
        df
        .join(real_likes, df._id == real_likes.post_id, "left")
        .drop("post_id")
        .withColumn("likes_count", F.coalesce(F.col("real_likes"), F.lit(0)))
        .drop("real_likes")
    )

    # Join author stats
    author_stats = user_stats.select(
        F.col("_id").alias("author_uid"),
        F.col("followers_count").alias("author_followers"),
        F.col("posts_count").alias("author_posts_count"),
        F.col("avg_likes_per_post").alias("author_avg_likes"),
        F.col("days_active").alias("author_days_active"),
    )

    df = (
        df
        .join(author_stats, df.user_id == author_stats.author_uid, "left")
        .drop("author_uid")
        .na.fill(0)
    )

    return df


def train(spark: SparkSession = None, silver_path: str = None,
          gold_path: str = None, output_path: str = None):
    """Entrena el modelo de predicción de engagement."""
    own_spark = spark is None
    if own_spark:
        spark = get_spark()
        spark.sparkContext.setLogLevel("WARN")

    silver_path = silver_path or str(SILVER_PATH)
    gold_path = gold_path or str(GOLD_PATH)
    output_path = output_path or str(GOLD_PATH / "models" / MODEL_NAME)

    print(f"{'='*60}")
    print(f"ENGAGEMENT PREDICTOR — Training")
    print(f"{'='*60}")

    # Build features
    df = build_features(spark, silver_path, gold_path)
    print(f"\nDataset: {df.count()} posts")
    print(f"Likes stats:")
    df.select("likes_count").describe().show()

    # Split
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

    # Pipeline
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features",
                            withStd=True, withMean=True)
    gbt = GBTRegressor(
        labelCol="likes_count", featuresCol="features",
        maxIter=50, maxDepth=6, seed=42,
    )
    pipeline = Pipeline(stages=[assembler, scaler, gbt])

    print("\nTraining GBTRegressor...")
    model = pipeline.fit(train_df)

    # Evaluate
    predictions = model.transform(test_df)
    rmse_eval = RegressionEvaluator(labelCol="likes_count", metricName="rmse")
    mae_eval = RegressionEvaluator(labelCol="likes_count", metricName="mae")
    r2_eval = RegressionEvaluator(labelCol="likes_count", metricName="r2")

    metrics = {
        "model": MODEL_NAME,
        "algorithm": "GBTRegressor",
        "rmse": round(rmse_eval.evaluate(predictions), 4),
        "mae": round(mae_eval.evaluate(predictions), 4),
        "r2": round(r2_eval.evaluate(predictions), 4),
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
    print(f"\nModel saved to {output_path}")

    if own_spark:
        spark.stop()

    return metrics


if __name__ == "__main__":
    train()
