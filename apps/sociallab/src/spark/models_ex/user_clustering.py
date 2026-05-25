"""Ejercicio ML-unsupervised-1 - clustering de usuarios (scaffold del alumno).

Este archivo es la version que ejecuta `./lab.sh train` cuando LAB_ML esta
vacio. Implementa `train(...)` manteniendo la firma publica para que
`src/spark/models/run_all.py` pueda importarlo.

Objetivo:
  - Agrupar usuarios no-spam a partir de `data/gold/user_stats`.
  - Probar varios valores de k y escoger el mejor por silhouette.
  - Guardar clusters y devolver metricas/perfiles para la vista Spark/ML.

Despues de implementar:
  1. Ejecuta `./lab.sh train`.
  2. Recarga la pestaña Spark/ML en la web.

No uses `./lab.sh unlock ml unsupervised` salvo que seas profesor y quieras
cargar la solucion oficial.
"""

from pyspark.sql import SparkSession

from src.config import GOLD_PATH
from infra.shared.spark import build_spark

MODEL_NAME = "user_clustering"

FEATURE_COLS = [
    "posts_count", "posts_per_day",
    "likes_given", "likes_received",
    "followers_count", "following_count",
    "avg_likes_per_post", "days_active",
]


def get_spark():
    return build_spark(f"SocialLab - {MODEL_NAME} (ex)")


def train(spark: SparkSession = None, input_path: str = None,
          output_path: str = None, k: int = 5):
    """
    EJERCICIO ML-unsupervised-1: Clustering de usuarios con KMeans.

    Agrupa usuarios por comportamiento, eligiendo el k optimo en
    [3, 4, 5, 6, 7] segun silhouette score.

    Pasos:
      1. Carga `gold/user_stats`, filtra `is_spam == False`, llena nulos con 0.
      2. Pipeline base: VectorAssembler + StandardScaler.
      3. Para cada k en range(3, 8):
            - Entrena KMeans(featuresCol="features", k=k, seed=42, maxIter=50)
            - Evalua con ClusteringEvaluator → silhouette
            - Guarda (k, silhouette) en una lista
      4. Elige el k con mayor silhouette → best_k.
      5. Reentrena pipeline completo con best_k.
      6. Calcula perfil de cada cluster (avg_posts, avg_likes_recv,
         avg_followers, avg_following, avg_posts_day).
      7. Etiqueta cada cluster basandote en el perfil:
            - posts_per_day > 2  → "Power User"
            - avg_followers > 1.5x media → "Influencer"
            - avg_posts < 5 → "Lurker"
            - avg_likes_recv > media → "Engaged Creator"
            - resto → "Regular User"
      8. Guarda los usuarios con cluster asignado en `output_path`.
      9. Devuelve dict con metricas, silhouette_scores por k, cluster_labels
         y cluster_sizes.

    Pistas:
      - El silhouette de KMeans en datos sinteticos suele ser bajo (0.2 — 0.3).
      - El etiquetado por reglas if/elif puede colapsar varios clusters al
        mismo nombre. Es esperado en el ejercicio: discutidlo en clase.
    """
    raise NotImplementedError(
        "EJERCICIO ML-unsupervised-1: KMeans con busqueda de k via silhouette. "
        "Devuelve perfiles de cluster y etiquetas heuristicas."
    )
