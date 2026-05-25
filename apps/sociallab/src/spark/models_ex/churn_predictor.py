"""Ejercicio ML-supervised-4 - predictor de churn (scaffold del alumno).

Este archivo es la version que ejecuta `./lab.sh train` cuando LAB_ML esta
vacio. Implementa `build_features(...)` y `train(...)` manteniendo sus firmas
publicas para que `src/spark/models/run_all.py` pueda importarlas.

Objetivo:
  - Construir features a nivel usuario.
  - Definir churn como inactividad durante `CHURN_DAYS`.
  - Entrenar un clasificador y analizar el efecto del data leakage.

Despues de implementar:
  1. Ejecuta `./lab.sh train`.
  2. Recarga la pestaña Spark/ML en la web.

No uses `./lab.sh unlock ml supervised` salvo que seas profesor y quieras
cargar la solucion oficial.

Predice si un usuario va a dejar de publicar.
"""

from pyspark.sql import SparkSession

from src.config import SILVER_PATH, GOLD_PATH
from infra.shared.spark import build_spark

MODEL_NAME = "churn_predictor"

CHURN_DAYS = 30  # Sin posts en los ultimos N dias = churn

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
    return build_spark(f"SocialLab - {MODEL_NAME} (ex)")


def build_features(spark: SparkSession, silver_path: str, gold_path: str):
    """
    EJERCICIO ML-supervised-4a: Features de churn.

    Lee silver/posts, silver/likes y gold/user_stats. Devuelve un DataFrame
    a nivel usuario (no spam) con las columnas de FEATURE_COLS.

    Definicion de churn:
        label = (days_since_last_post >= CHURN_DAYS) ? 1.0 : 0.0

    Calcula:
      - posts_count, posts_per_day, days_active   → ya estan en user_stats
      - days_since_last_post  → datediff(max(created_at globalmente),
                                           max(created_at del usuario))
      - recent_posts_ratio    → posts en la 2a mitad / total posts
      - recent_likes_ratio    → likes recibidos en la 2a mitad / total
      - likes_received, likes_given, followers_count, following_count → joins

    Pistas:
      - Para "recent" usa el midpoint temporal:
            midpoint = posts.agg(F.expr("percentile_approx(unix_timestamp(created_at), 0.5)"))
            ...collect()[0][0]
      - F.unix_timestamp("created_at") > midpoint → 1, else 0, sumar.

    OJO con el data leakage: la feature `days_since_last_post` define la
    label directamente. Se incluye a proposito para que veais lo que pasa
    cuando una feature es proxy del target. Discutidlo en clase.
    """
    raise NotImplementedError(
        "EJERCICIO ML-supervised-4a: construye build_features para churn (incluye "
        "days_since_last_post y ratios temporales recent vs old)."
    )


def train(spark: SparkSession = None, silver_path: str = None,
          gold_path: str = None, output_path: str = None):
    """
    EJERCICIO ML-supervised-4b: Predictor de churn con GBTClassifier.

    Pasos identicos a los otros clasificadores supervisados:
      1. build_features() para obtener el dataset.
      2. Split 80/20 (seed=42).
      3. Pipeline: VectorAssembler + StandardScaler + GBTClassifier(
            labelCol="label", maxIter=50, maxDepth=6, seed=42).
      4. Evalua AUC + multiclass metrics.
      5. Guarda modelo + predicciones.
      6. Devuelve dict con metricas + feature_importance + churn_threshold_days.

    Espera AUC ~ 1.0 por el data leakage comentado en build_features.
    """
    raise NotImplementedError(
        "EJERCICIO ML-supervised-4b: entrena GBTClassifier de churn. Reporta el AUC y "
        "discute por que sale tan alto (pista: data leakage)."
    )
