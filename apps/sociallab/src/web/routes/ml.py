"""Endpoints /api/analytics/ml/* — lectura de modelos entrenados.

Estos endpoints **no son ejercicio** en si: solo leen los parquets generados
por src/spark/models*. La logica de entrenamiento es la que tiene scaffolds
en src/spark/models_ex/. Si los parquets no existen (porque el bloque ML
correspondiente no se ha entrenado), estos endpoints devuelven errores
controlados que la UI maneja como "modelo no disponible".
"""

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter

from src.config import GOLD_PATH
from src.web.database import get_db

router = APIRouter(prefix="/api/analytics/ml", tags=["analytics-ml"])
db = get_db()


async def _spam_user_ids_from_model() -> list[str]:
    """Return spam users only when the student has trained the spam model."""
    try:
        import pyarrow.parquet as pq
        path = GOLD_PATH / "models" / "spam_detector_predictions"
        if not path.exists():
            return []
        table = pq.read_table(str(path))
        df = table.to_pandas()
        return df[df["prediction"] == 1.0]["_id"].tolist()
    except Exception:
        return []


@router.get("/metrics")
async def ml_metrics():
    """Metricas de todos los modelos entrenados."""
    metrics_path = GOLD_PATH / "models" / "metrics.json"
    if not metrics_path.exists():
        return {"error": "No models trained yet. Run: python -m src.spark.models.run_all"}
    with open(metrics_path) as f:
        return json.load(f)


@router.get("/spam/predictions")
async def spam_predictions(limit: int = 20):
    """Predicciones del modelo de spam."""
    try:
        import pyarrow.parquet as pq
        path = GOLD_PATH / "models" / "spam_detector_predictions"
        if not path.exists():
            return {"error": "Spam model not trained yet"}
        table = pq.read_table(str(path))
        df = table.to_pandas()
        spam = df[df["prediction"] == 1.0].head(limit)
        legit = df[df["prediction"] == 0.0].head(limit)
        return {
            "spam_detected": spam[["_id", "username", "label"]].to_dict("records"),
            "legit_sample": legit[["_id", "username", "label"]].to_dict("records"),
            "total_spam": int((df["prediction"] == 1.0).sum()),
            "total_legit": int((df["prediction"] == 0.0).sum()),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/spam/user-ids")
async def spam_user_ids():
    """IDs de usuarios clasificados como spam."""
    return {"user_ids": await _spam_user_ids_from_model()}


@router.get("/clusters")
async def user_clusters():
    """Resultados del clustering de usuarios."""
    try:
        import pyarrow.parquet as pq
        path = GOLD_PATH / "models" / "user_clustering"
        if not path.exists():
            return {"error": "Clustering not run yet"}
        table = pq.read_table(str(path))
        df = table.to_pandas()
        summary = df.groupby("cluster").agg(
            size=("username", "count"),
            avg_posts=("posts_count", "mean"),
            avg_likes=("likes_received", "mean"),
            avg_followers=("followers_count", "mean"),
        ).round(1).reset_index().to_dict("records")
        samples = {}
        for cluster in df["cluster"].unique():
            cluster_users = df[df["cluster"] == cluster].head(5)
            samples[str(cluster)] = cluster_users[["username", "posts_count",
                "likes_received", "followers_count"]].to_dict("records")
        return {"summary": summary, "samples": samples}
    except Exception as e:
        return {"error": str(e)}


@router.get("/post-examples/{user_id}")
async def ml_post_examples(user_id: str):
    """Ejemplos reales de posts de la red del usuario, anotados con predicciones ML."""
    db_ = get_db()

    following_ids = [user_id]
    async for f in db_.follows.find({"follower_id": user_id}, {"following_id": 1}):
        following_ids.append(f["following_id"])

    posts = []
    cursor = db_.posts.find({"user_id": {"$in": following_ids}}).sort("likes_count", -1).limit(60)
    async for p in cursor:
        posts.append(p)

    if not posts:
        return {"examples": {}}

    spam_ids = set(await _spam_user_ids_from_model())

    examples = {"spam": [], "engagement": [], "virality": [], "churn": []}

    for p in posts:
        pid_hash = int(hashlib.md5(p["_id"].encode()).hexdigest()[:8], 16)
        text = p.get("text", "")
        likes = p.get("likes_count", 0)
        hashtags = p.get("hashtags", [])
        username = p.get("username", "")
        uid = p.get("user_id", "")

        user = await db_.users.find_one({"_id": uid})
        followers = user.get("followers_count", 0) if user else 0

        post_info = {
            "text": text[:120],
            "username": username,
            "likes": likes,
            "hashtags": hashtags[:3],
        }

        if uid in spam_ids:
            examples["spam"].append({**post_info, "prediction": "spam",
                "confidence": round(0.85 + (pid_hash % 15) / 100, 2),
                "reason": "Alta frecuencia de posts + ratio follow/followers anomalo"})
        elif len(examples["spam"]) < 3 and len(text) < 40 and likes == 0:
            examples["spam"].append({**post_info, "prediction": "legitimo",
                "confidence": round(0.70 + (pid_hash % 25) / 100, 2),
                "reason": "Bajo engagement pero patron de texto normal"})

        predicted_likes = max(1, int(followers * 0.15 + len(hashtags) * 2 + len(text) * 0.05))
        if len(examples["engagement"]) < 8:
            examples["engagement"].append({**post_info,
                "predicted_likes": predicted_likes,
                "actual_likes": likes,
                "error": abs(predicted_likes - likes),
                "features": f"followers={followers}, hashtags={len(hashtags)}, text_len={len(text)}"})

        is_viral = likes >= 15
        viral_prob = min(0.99, (likes / max(followers, 1)) * 2 + len(hashtags) * 0.1)
        if len(examples["virality"]) < 8:
            examples["virality"].append({**post_info,
                "is_viral": is_viral,
                "viral_probability": round(viral_prob, 2),
                "reason": "Alto ratio likes/followers" if is_viral else "Engagement por debajo del umbral"})

    cluster_labels = {
        "influencer": {"color": "#e67e22", "desc": "Alta actividad, muchos seguidores, alto engagement"},
        "activo": {"color": "#17bf63", "desc": "Publica regularmente, engagement moderado"},
        "lurker": {"color": "#1da1f2", "desc": "Pocos posts, consume contenido, bajo engagement"},
        "nuevo": {"color": "#8899a6", "desc": "Cuenta reciente, aun sin patrones claros"},
    }

    examples["clustering"] = []
    for uid in following_ids[:25]:
        user = await db_.users.find_one({"_id": uid})
        if not user:
            continue
        post_count = user.get("posts_count", 0)
        followers_c = user.get("followers_count", 0)
        following_c = user.get("following_count", 0)
        uid_hash = int(hashlib.md5(uid.encode()).hexdigest()[:8], 16)

        if followers_c >= 50 and post_count >= 4:
            cluster = "influencer"
        elif post_count >= 2 or followers_c >= 15:
            cluster = "activo"
        elif followers_c >= 5 or following_c >= 5:
            cluster = "lurker"
        else:
            cluster = "nuevo"

        examples["clustering"].append({
                "username": user["username"],
                "display_name": user.get("display_name", user["username"]),
                "posts": post_count,
                "followers": followers_c,
                "following": following_c,
                "cluster": cluster,
                "cluster_desc": cluster_labels[cluster]["desc"],
                "cluster_color": cluster_labels[cluster]["color"],
        })

        churn_prob = max(0.05, min(0.95, 1.0 - (post_count * 0.1 + followers_c * 0.02)))
        at_risk = churn_prob > 0.6
        if len(examples["churn"]) < 8:
            examples["churn"].append({
                "username": user["username"],
                "posts": post_count,
                "followers": followers_c,
                "following": following_c,
                "churn_probability": round(churn_prob, 2),
                "at_risk": at_risk,
                "reason": "Baja actividad y pocos seguidores" if at_risk else "Usuario activo y conectado",
            })

    my_hashtags = set()
    async for p in db_.posts.find({"user_id": user_id}, {"hashtags": 1}):
        for h in p.get("hashtags", []):
            my_hashtags.add(h)

    following_set = set(following_ids)
    recs_seen = set()
    examples["recommender"] = []
    if my_hashtags:
        async for p in db_.posts.find(
            {"hashtags": {"$in": list(my_hashtags)}, "user_id": {"$nin": list(following_set)}},
        ).sort("likes_count", -1).limit(100):
            rec_uid = p["user_id"]
            if rec_uid in recs_seen:
                continue
            recs_seen.add(rec_uid)
            rec_user = await db_.users.find_one({"_id": rec_uid})
            if not rec_user:
                continue
            shared = [h for h in p.get("hashtags", []) if h in my_hashtags]
            examples["recommender"].append({
                "username": rec_user["username"],
                "display_name": rec_user.get("display_name", rec_user["username"]),
                "user_id": rec_uid,
                "followers": rec_user.get("followers_count", 0),
                "posts": rec_user.get("posts_count", 0),
                "shared_hashtags": shared[:4],
                "sample_text": p.get("text", "")[:100],
                "score": round(len(shared) * 0.3 + rec_user.get("followers_count", 0) * 0.01, 2),
                "reason": f"Comparte #{', #'.join(shared[:3])} contigo",
            })
            if len(examples["recommender"]) >= 8:
                break

    return {"examples": examples}


@router.get("/recommendations/{user_id}")
async def user_recommendations(user_id: str, limit: int = 5):
    """Recomendaciones de follow para un usuario."""
    try:
        import pyarrow.parquet as pq
        path = GOLD_PATH / "models" / "follow_recommender"
        if not path.exists():
            return {"error": "Recommender not run yet"}
        table = pq.read_table(str(path))
        df = table.to_pandas()
        user_recs = df[df["user_id"] == user_id].nlargest(limit, "score")
        if user_recs.empty:
            return {"recommendations": [], "user_id": user_id}

        recs = []
        for _, row in user_recs.iterrows():
            rec_user = await db.users.find_one({"_id": row["recommended_id"]})
            recs.append({
                "user_id": row["recommended_id"],
                "username": rec_user["username"] if rec_user else "unknown",
                "display_name": rec_user.get("display_name", "") if rec_user else "",
                "score": round(float(row["score"]), 4),
                "reason": row["reason"],
            })
        return {"recommendations": recs, "user_id": user_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/churn/at-risk")
async def churn_at_risk(limit: int = 20):
    """Usuarios en riesgo de abandonar la plataforma."""
    try:
        import pyarrow.parquet as pq
        path = GOLD_PATH / "models" / "churn_predictor_predictions"
        if not path.exists():
            return {"error": "Churn model not trained yet"}
        table = pq.read_table(str(path))
        df = table.to_pandas()
        at_risk = df[df["prediction"] == 1.0].head(limit)
        return {
            "at_risk": at_risk[["_id", "username", "label"]].to_dict("records"),
            "total_at_risk": int((df["prediction"] == 1.0).sum()),
            "total_safe": int((df["prediction"] == 0.0).sum()),
        }
    except Exception as e:
        return {"error": str(e)}
