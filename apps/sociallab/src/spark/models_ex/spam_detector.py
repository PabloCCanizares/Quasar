"""Ejercicio ML-supervised-1 - detector de spam (scaffold del alumno).

Este archivo es la version que ejecuta `./lab.sh train` cuando LAB_ML esta
vacio. Implementa `train(...)` manteniendo la firma publica para que
`src/spark/models/run_all.py` pueda importarlo.

Objetivo:
  - Entrenar un Pipeline de Spark ML sobre `data/gold/spam_features`.
  - Guardar el modelo y las predicciones en `data/gold/models/`.
  - Devolver un dict de metricas para que la vista Spark/ML pueda mostrarlo.

Despues de implementar:
  1. Ejecuta `./lab.sh train`.
  2. Recarga la pestaña Spark/ML en la web.

No uses `./lab.sh unlock ml supervised` salvo que seas profesor y quieras
cargar la solucion oficial.

Dataset: data/gold/spam_features (parquet, generado por etl_gold).
Features disponibles (ya calculadas):
    posts_count, posts_per_day, avg_text_length, unique_texts_ratio,
    avg_hashtags_per_post, likes_given, likes_received,
    followers_count, following_count, follow_ratio, days_active

Label: is_spam (0 / 1) — ya viene como columna 'label' en el parquet.

Tu trabajo: leer features, montar Pipeline, entrenar, evaluar y guardar.
"""

from pyspark.sql import SparkSession

from infra.shared.spark import build_spark
from src.config import GOLD_PATH

MODEL_NAME = "spam_detector"

FEATURE_COLS = [
    "posts_count", "posts_per_day", "avg_text_length",
    "unique_texts_ratio", "avg_hashtags_per_post",
    "likes_given", "likes_received",
    "followers_count", "following_count", "follow_ratio",
    "days_active",
]


def get_spark():
    return build_spark(f"SocialLab - {MODEL_NAME} (ex)")


def train(spark: SparkSession = None, input_path: str = None, output_path: str = None):
    """
    EJERCICIO ML-supervised-1: Detector de spam con RandomForest.

    Pasos:
      1. Carga el parquet `gold/spam_features` como DataFrame de Spark.
      2. Llena nulos con 0 (`df.na.fill(0)`).
      3. Construye un Pipeline con tres stages:
            - VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
            - StandardScaler(inputCol="raw_features", outputCol="features",
                             withStd=True, withMean=True)
            - RandomForestClassifier(labelCol="label", featuresCol="features",
                                     numTrees=100, maxDepth=8, seed=42)
      4. Split 80/20 con seed=42, ajusta el pipeline al train.
      5. Predice sobre test y evalua AUC (BinaryClassificationEvaluator) y
         accuracy/precision/recall/f1 (MulticlassClassificationEvaluator).
      6. Guarda el pipeline en `output_path` (default: gold/models/spam_detector).
      7. Guarda las predicciones en `output_path + "_predictions"`.
      8. Devuelve un dict con metricas y feature_importance.

    Pistas:
      - El `pipeline.fit(train_df)` devuelve un PipelineModel con .stages.
      - rf_model.featureImportances es un Vector denso con la importancia
        relativa de cada columna de FEATURE_COLS (mismo orden).
      - run_all.py espera que train() devuelva el dict de metricas.

    Returns:
        dict con: {model, algorithm, auc, accuracy, precision, recall, f1,
                   train_size, test_size, feature_importance}
    """
    raise NotImplementedError(
        "EJERCICIO ML-supervised-1: implementa el entrenamiento del detector de spam. "
        "Lee gold/spam_features, monta Pipeline (VectorAssembler+StandardScaler+RandomForest) "
        "y devuelve metricas + feature importance."
    )
