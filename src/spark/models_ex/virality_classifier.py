"""Ejercicio ML-supervised-3 - clasificador de viralidad (scaffold del alumno).

Este archivo es la version que ejecuta `./lab.sh train` cuando LAB_ML esta
vacio. Implementa `train(...)` manteniendo la firma publica para que
`src/spark/models/run_all.py` pueda importarlo.

Objetivo:
  - Reutilizar `build_features(...)` de `engagement_predictor.py`.
  - Convertir likes recibidos en una etiqueta binaria de viralidad.
  - Entrenar un clasificador y devolver metricas interpretables.

Despues de implementar:
  1. Resuelve primero `engagement_predictor.py`.
  2. Ejecuta `./lab.sh train`.
  3. Recarga la pestaña Spark/ML en la web.

No uses `./lab.sh unlock ml supervised` salvo que seas profesor y quieras
cargar la solucion oficial.

Reutiliza `build_features` del scaffold de engagement_predictor.
"""

import os
from pyspark.sql import SparkSession

from src.config import SPARK_MASTER, SILVER_PATH, GOLD_PATH, IS_LOCAL
from src.spark.models_ex.engagement_predictor import build_features

MODEL_NAME = "virality_classifier"

FEATURE_COLS = [
    "num_hashtags", "text_length",
    "hour_of_day", "day_of_week",
    "author_followers", "author_posts_count",
    "author_avg_likes", "author_days_active",
]


def get_spark():
    if IS_LOCAL:
        java17 = "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
        if os.path.exists(java17):
            os.environ["JAVA_HOME"] = java17
    return (
        SparkSession.builder
        .master(SPARK_MASTER)
        .appName(f"SocialLab - {MODEL_NAME} (ex)")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def train(spark: SparkSession = None, silver_path: str = None,
          gold_path: str = None, output_path: str = None):
    """
    EJERCICIO ML-supervised-3: Clasificador de viralidad con LogisticRegression.

    Define "viral" como un post con likes >= percentil 90 del dataset.

    Pasos:
      1. Llama a build_features() (del scaffold engagement_predictor) — requiere
         que ese ejercicio este resuelto antes.
      2. Calcula el umbral viral con `df.approxQuantile('likes_count', [0.9], 0.01)[0]`.
      3. Crea la columna `label = (likes_count >= threshold)` como 0.0 o 1.0.
      4. Split 80/20 (seed=42).
      5. Pipeline: VectorAssembler + StandardScaler + LogisticRegression(
            labelCol="label", maxIter=100, regParam=0.01).
      6. Evalua AUC + accuracy/precision/recall/f1.
      7. Extrae los coeficientes (lr_model.coefficients.toArray()) — son la
         interpretabilidad de LogisticRegression, ordena por valor absoluto.
      8. Guarda el modelo y devuelve dict con metricas + coefficients +
         viral_threshold_likes.
    """
    raise NotImplementedError(
        "EJERCICIO ML-supervised-3: entrena LogisticRegression para clasificar virales. "
        "Define label con percentil 90 de likes_count y reporta AUC + coefficients."
    )
