"""Ejercicio ML-graph_ml-1 - recomendador de follows (scaffold del alumno).

Este archivo es la version que ejecuta `./lab.sh train` cuando LAB_ML esta
vacio. Implementa `build_recommendations(...)` manteniendo la firma publica
para que `src/spark/models/run_all.py` pueda importarlo.

Objetivo:
  - Construir recomendaciones de follow con senales de grafo.
  - Combinar hashtags compartidos y amigos-de-amigos en un score.
  - Guardar recomendaciones y devolver metricas para la vista Spark/ML.

Despues de implementar:
  1. Ejecuta `./lab.sh train`.
  2. Recarga la pestaña Spark/ML en la web.

No uses `./lab.sh unlock ml graph_ml` salvo que seas profesor y quieras cargar
la solucion oficial.

No es ML clasico, sino scoring sobre el grafo: combina senales de hashtags
compartidos y "amigos de amigos" (friends-of-friends).
"""

from pyspark.sql import SparkSession

from src.config import SILVER_PATH, GOLD_PATH
from infra.shared.spark import build_spark

MODEL_NAME = "follow_recommender"


def get_spark():
    return build_spark(f"SocialLab - {MODEL_NAME} (ex)")


def build_recommendations(spark: SparkSession = None, silver_path: str = None,
                           gold_path: str = None, output_path: str = None):
    """
    EJERCICIO ML-graph_ml-1: Recomendaciones de follow.

    Para cada usuario, calcula los 10 mejores candidatos a seguir, basandote
    en dos senales del grafo. Output:
        DataFrame con (user_id, recommended_id, score, hashtag_score,
                       fof_score, reason)

    Senales:
      A) shared_hashtags — pares (a, b) que coinciden en hashtags. Para cada
         par, cuenta cuantos hashtags comparten y normaliza por el maximo
         observado → hashtag_score in [0, 1].

      B) friends_of_friends — pares (a, c) tales que existe b con a→b→c.
         Cuenta cuantos b distintos hay para cada par y normaliza → fof_score.

    Combinacion: score = 0.6 * hashtag_score + 0.4 * fof_score.

    Reglas adicionales:
      - Excluye pares que ya se siguen (left_anti contra silver/follows).
      - Hazlo bidireccional: si recomiendas b a a, tambien recomienda a a b.
      - Quedate con top 10 por user_id (Window + row_number).
      - Asigna `reason` segun los componentes:
            * hashtag>0 y fof>0  → "Intereses comunes + amigos en comun"
            * solo hashtag>0     → "Intereses similares"
            * solo fof>0         → "Amigos en comun"

    Devuelve dict de metricas:
        {model, algorithm, total_recommendations, users_with_recommendations,
         avg_score}

    Pistas:
      - Para shared_hashtags evita pares duplicados con `a.user_id < b.user_id`.
      - Para FoF: dos joins de la misma tabla follows, primero ab y luego bc,
        filtra `ab.follower_id != bc.following_id` para no recomendarse a si
        mismo.
      - max_shared = shared_tags.agg(F.max('shared_tags')).collect()[0][0] or 1.
    """
    raise NotImplementedError(
        "EJERCICIO ML-graph_ml-1: implementa build_recommendations combinando hashtags "
        "compartidos (peso 0.6) y friends-of-friends (peso 0.4)."
    )
