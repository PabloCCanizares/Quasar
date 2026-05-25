"""
Modelo 1: Detección de Spam/Bots

Clasifica usuarios como spam o legítimos usando las features
construidas en el ETL (gold/spam_features).

Features:
  - posts_count, posts_per_day
  - avg_text_length, unique_texts_ratio
  - avg_hashtags_per_post
  - likes_given, likes_received
  - followers_count, following_count, follow_ratio
  - days_active

Label: is_spam (0/1)

Modelo: RandomForest + evaluación con métricas.
"""

from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import RandomForestClassifier, GBTClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import functions as F

from src.config import GOLD_PATH
from infra.shared.spark import build_spark

MODEL_NAME = "spam_detector"

FEATURE_COLS = [
    "posts_count", "posts_per_day", "avg_text_length",
    "unique_texts_ratio", "avg_hashtags_per_post",
    "likes_given", "likes_received",
    "followers_count", "following_count", "follow_ratio",
    "days_active",
]


def get_spark():
    return build_spark(f"SocialLab - {MODEL_NAME}")


def train(spark: SparkSession = None, input_path: str = None, output_path: str = None):
    """Entrena el modelo de detección de spam."""
    own_spark = spark is None
    if own_spark:
        spark = get_spark()
        spark.sparkContext.setLogLevel("WARN")

    input_path = input_path or str(GOLD_PATH / "spam_features")
    output_path = output_path or str(GOLD_PATH / "models" / MODEL_NAME)

    print(f"{'='*60}")
    print(f"SPAM DETECTOR — Training")
    print(f"{'='*60}")

    # Load features
    df = spark.read.parquet(input_path)
    df = df.na.fill(0)

    # Show class balance
    print("\nClass distribution:")
    df.groupBy("label").count().show()

    # Split
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    print(f"Train: {train_df.count()}, Test: {test_df.count()}")

    # Pipeline
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features",
                            withStd=True, withMean=True)
    rf = RandomForestClassifier(
        labelCol="label", featuresCol="features",
        numTrees=100, maxDepth=8, seed=42,
    )
    pipeline = Pipeline(stages=[assembler, scaler, rf])

    # Train
    print("\nTraining RandomForest...")
    model = pipeline.fit(train_df)

    # Predict
    predictions = model.transform(test_df)

    # Evaluate
    auc_eval = BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC")
    mc_eval = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")

    auc = auc_eval.evaluate(predictions)
    accuracy = mc_eval.evaluate(predictions, {mc_eval.metricName: "accuracy"})
    precision = mc_eval.evaluate(predictions, {mc_eval.metricName: "weightedPrecision"})
    recall = mc_eval.evaluate(predictions, {mc_eval.metricName: "weightedRecall"})
    f1 = mc_eval.evaluate(predictions, {mc_eval.metricName: "f1"})

    metrics = {
        "model": MODEL_NAME,
        "algorithm": "RandomForest",
        "auc": round(auc, 4),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "train_size": train_df.count(),
        "test_size": test_df.count(),
    }

    print(f"\nResults:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Feature importance
    rf_model = model.stages[-1]
    importances = list(zip(FEATURE_COLS, rf_model.featureImportances.toArray()))
    importances.sort(key=lambda x: x[1], reverse=True)
    print(f"\nFeature Importance:")
    for feat, imp in importances:
        print(f"  {feat}: {imp:.4f}")

    metrics["feature_importance"] = {f: round(float(v), 4) for f, v in importances}

    # Save model
    model.write().overwrite().save(output_path)
    print(f"\nModel saved to {output_path}")

    # Save predictions for analysis
    (
        predictions
        .select("_id", "username", "label", "prediction", "probability")
        .write.parquet(f"{output_path}_predictions", mode="overwrite")
    )

    if own_spark:
        spark.stop()

    return metrics


def predict(spark: SparkSession, model_path: str, df):
    """Aplica el modelo a nuevos datos."""
    from pyspark.ml import PipelineModel
    model = PipelineModel.load(model_path)
    return model.transform(df)


if __name__ == "__main__":
    train()
