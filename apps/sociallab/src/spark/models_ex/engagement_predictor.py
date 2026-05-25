"""Ejercicio ML-supervised-2 - prediccion de engagement (scaffold del alumno).

Este archivo es la version que ejecuta `./lab.sh train` cuando LAB_ML esta
vacio. Implementa `build_features(...)` y `train(...)` manteniendo sus firmas
publicas para que `src/spark/models/run_all.py` pueda importarlas.

Objetivo:
  - Construir un dataset de features a nivel post.
  - Entrenar un modelo de regresion para predecir likes recibidos.
  - Guardar el modelo en `data/gold/models/` y devolver metricas.

Despues de implementar:
  1. Ejecuta `./lab.sh train`.
  2. Recarga la pestaña Spark/ML en la web.

No uses `./lab.sh unlock ml supervised` salvo que seas profesor y quieras
cargar la solucion oficial.

Predice cuantos likes recibira un post (regresion). Reutilizable: el bloque
de virality (clasificacion binaria) llama a `build_features` desde aqui.
"""

from pyspark.sql import SparkSession

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
    return build_spark(f"SocialLab - {MODEL_NAME} (ex)")


def build_features(spark: SparkSession, silver_path: str, gold_path: str):
    """
    EJERCICIO ML-supervised-2a: Construir el dataset de features.

    Lee silver/posts, silver/likes y gold/user_stats. Devuelve un DataFrame
    de posts NO-spam con estas columnas (todas las que estan en FEATURE_COLS
    + `likes_count`, que es la label):

        num_hashtags        F.size(hashtags)
        text_length         F.length(text)
        hour_of_day         F.hour(created_at)
        day_of_week         F.dayofweek(created_at)
        author_followers    desde gold/user_stats
        author_posts_count  desde gold/user_stats
        author_avg_likes    desde gold/user_stats
        author_days_active  desde gold/user_stats
        likes_count         conteo real de likes por post (NO el del raw)

    Pistas:
      - Filtra `posts.is_spam == False` antes de calcular features.
      - Los likes reales: `likes.groupBy('post_id').agg(F.count('*').alias('real_likes'))`.
      - Une author stats por user_id (`F.col('_id').alias('author_uid')` ayuda).
      - Llena nulos con 0 al final.
    """
    raise NotImplementedError(
        "EJERCICIO ML-supervised-2a: construye build_features para engagement_predictor. "
        "Lee posts, likes, user_stats y devuelve un DF con FEATURE_COLS + likes_count."
    )


def train(spark: SparkSession = None, silver_path: str = None,
          gold_path: str = None, output_path: str = None):
    """
    EJERCICIO ML-supervised-2b: Predictor de engagement con GBTRegressor.

    Pasos:
      1. Llama a build_features() para obtener el dataset.
      2. Split 80/20 (seed=42).
      3. Pipeline: VectorAssembler + StandardScaler + GBTRegressor(
            labelCol="likes_count", maxIter=50, maxDepth=6, seed=42).
      4. Evalua con RegressionEvaluator: rmse, mae, r2.
      5. Guarda el pipeline en gold/models/engagement_predictor.
      6. Devuelve dict con {model, algorithm, rmse, mae, r2,
         train_size, test_size, feature_importance}.

    Nota: con datos sinteticos el R^2 va a salir bajisimo (cercano a 0).
    Es esperado — los datos no tienen senal real, sirve como ejemplo de
    "modelo correcto pero datos pobres".
    """
    raise NotImplementedError(
        "EJERCICIO ML-supervised-2b: entrena GBTRegressor con build_features() y devuelve metricas."
    )
