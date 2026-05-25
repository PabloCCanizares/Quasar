"""
Modelo 3: Clasificación de Viralidad

¿Este post va a ser viral? (supera el percentil 90 de likes)

Mismas features que engagement, pero clasificación binaria.

Label: is_viral (0/1) — 1 si likes > percentil 90

Modelo: LogisticRegression + RandomForest.
"""

from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import functions as F

from src.config import SILVER_PATH, GOLD_PATH
from infra.shared.spark import build_spark
from src.spark.models.engagement_predictor import build_features

MODEL_NAME = "virality_classifier"

FEATURE_COLS = [
    "num_hashtags", "text_length",
    "hour_of_day", "day_of_week",
    "author_followers", "author_posts_count",
    "author_avg_likes", "author_days_active",
]


def get_spark():
    return build_spark(f"SocialLab - {MODEL_NAME}")


def train(spark: SparkSession = None, silver_path: str = None,
          gold_path: str = None, output_path: str = None):
    """Entrena el clasificador de viralidad."""
    own_spark = spark is None
    if own_spark:
        spark = get_spark()
        spark.sparkContext.setLogLevel("WARN")

    silver_path = silver_path or str(SILVER_PATH)
    gold_path = gold_path or str(GOLD_PATH)
    output_path = output_path or str(GOLD_PATH / "models" / MODEL_NAME)

    print(f"{'='*60}")
    print(f"VIRALITY CLASSIFIER — Training")
    print(f"{'='*60}")

    # Build features (reuse from engagement)
    df = build_features(spark, silver_path, gold_path)

    # Define viral threshold (percentile 90)
    threshold = df.approxQuantile("likes_count", [0.9], 0.01)[0]
    print(f"\nViral threshold (p90): {threshold} likes")

    df = df.withColumn(
        "label",
        F.when(F.col("likes_count") >= threshold, 1.0).otherwise(0.0)
    )

    print("Class distribution:")
    df.groupBy("label").count().show()

    # Split
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

    # Pipeline with LogisticRegression
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features",
                            withStd=True, withMean=True)
    lr = LogisticRegression(
        labelCol="label", featuresCol="features",
        maxIter=100, regParam=0.01,
    )
    pipeline = Pipeline(stages=[assembler, scaler, lr])

    print("\nTraining LogisticRegression...")
    model = pipeline.fit(train_df)
    predictions = model.transform(test_df)

    # Evaluate
    auc_eval = BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC")
    mc_eval = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")

    metrics = {
        "model": MODEL_NAME,
        "algorithm": "LogisticRegression",
        "viral_threshold_likes": threshold,
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

    # Coefficients
    lr_model = model.stages[-1]
    coeffs = list(zip(FEATURE_COLS, lr_model.coefficients.toArray()))
    coeffs.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"\nCoefficients:")
    for feat, coef in coeffs:
        print(f"  {feat}: {coef:.4f}")

    metrics["coefficients"] = {f: round(float(v), 4) for f, v in coeffs}

    # Save
    model.write().overwrite().save(output_path)
    print(f"\nModel saved to {output_path}")

    if own_spark:
        spark.stop()

    return metrics


if __name__ == "__main__":
    train()
