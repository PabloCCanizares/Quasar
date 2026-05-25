"""
Spark ETL: Silver → Gold

Genera tablas analíticas que alimentan la app y sirven para modelos ML:
  1. user_stats      — engagement, actividad, contadores por usuario
  2. post_rankings   — posts ordenados por engagement
  3. hashtag_trends  — trending hashtags por ventana temporal
  4. spam_features   — features para modelo de detección de spam
  5. community_edges — aristas para cargar en Neo4j (comunidades)

Cada función recibe SparkSession + rutas. Mismo código local y Databricks.
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window


# ========================================================
# 1. USER STATS
# ========================================================

def gold_user_stats(spark: SparkSession, silver_path: str, output_path: str):
    """
    Calcula métricas por usuario:
    - posts_count, likes_given, likes_received
    - followers_count, following_count
    - avg_likes_per_post
    - days_active, posts_per_day
    - is_spam (propagated from silver)
    """
    users = spark.read.parquet(f"{silver_path}/users")
    posts = spark.read.parquet(f"{silver_path}/posts")
    likes = spark.read.parquet(f"{silver_path}/likes")
    follows = spark.read.parquet(f"{silver_path}/follows")

    # Posts per user
    posts_count = posts.groupBy("user_id").agg(
        F.count("*").alias("posts_count"),
        F.min("created_at").alias("first_post_at"),
        F.max("created_at").alias("last_post_at"),
    )

    # Likes given per user
    likes_given = likes.groupBy("user_id").agg(
        F.count("*").alias("likes_given")
    )

    # Likes received per user (through their posts)
    post_user = posts.select("_id", "user_id")
    likes_received = (
        likes
        .join(post_user, likes.post_id == post_user._id, "inner")
        .groupBy(post_user.user_id.alias("author_id"))
        .agg(F.count("*").alias("likes_received"))
    )

    # Followers/following count
    followers_count = follows.groupBy("following_id").agg(
        F.count("*").alias("followers_count")
    )
    following_count = follows.groupBy("follower_id").agg(
        F.count("*").alias("following_count")
    )

    # Join everything onto users
    stats = (
        users.select("_id", "username", "display_name", "is_spam", "origin", "created_at")
        .join(posts_count, users._id == posts_count.user_id, "left")
        .drop(posts_count.user_id)
        .join(likes_given, users._id == likes_given.user_id, "left")
        .drop(likes_given.user_id)
        .join(likes_received, users._id == likes_received.author_id, "left")
        .drop("author_id")
        .join(followers_count, users._id == followers_count.following_id, "left")
        .drop("following_id")
        .join(following_count, users._id == following_count.follower_id, "left")
        .drop("follower_id")
        .fillna(0, subset=["posts_count", "likes_given", "likes_received",
                           "followers_count", "following_count"])
    )

    # Derived metrics
    stats = (
        stats
        .withColumn(
            "avg_likes_per_post",
            F.when(F.col("posts_count") > 0,
                   F.col("likes_received") / F.col("posts_count"))
            .otherwise(0)
        )
        .withColumn(
            "days_active",
            F.when(F.col("first_post_at").isNotNull(),
                   F.datediff(F.col("last_post_at"), F.col("first_post_at")) + 1)
            .otherwise(0)
        )
        .withColumn(
            "posts_per_day",
            F.when(F.col("days_active") > 0,
                   F.col("posts_count") / F.col("days_active"))
            .otherwise(0)
        )
        .drop("first_post_at", "last_post_at")
    )

    stats.write.parquet(output_path, mode="overwrite")
    print(f"Gold user_stats: {stats.count()} rows → {output_path}")
    return stats


# ========================================================
# 2. POST RANKINGS
# ========================================================

def gold_post_rankings(spark: SparkSession, silver_path: str, output_path: str):
    """
    Calcula ranking de posts por engagement real (likes recibidos).
    """
    posts = spark.read.parquet(f"{silver_path}/posts")
    likes = spark.read.parquet(f"{silver_path}/likes")

    # Real likes count (not the dirty one from raw)
    real_likes = likes.groupBy("post_id").agg(
        F.count("*").alias("real_likes_count")
    )

    ranked = (
        posts
        .filter(F.col("is_spam") == False)  # noqa: E712
        .join(real_likes, posts._id == real_likes.post_id, "left")
        .drop(real_likes.post_id)
        .fillna(0, subset=["real_likes_count"])
        .withColumn("likes_count", F.col("real_likes_count"))
        .drop("real_likes_count")
        .withColumn("rank", F.row_number().over(
            Window.orderBy(F.col("likes_count").desc(), F.col("created_at").desc())
        ))
    )

    ranked.write.parquet(output_path, mode="overwrite")
    print(f"Gold post_rankings: {ranked.count()} rows → {output_path}")
    return ranked


# ========================================================
# 3. HASHTAG TRENDS
# ========================================================

def gold_hashtag_trends(spark: SparkSession, silver_path: str, output_path: str):
    """
    Trending hashtags: cuenta posts por hashtag por día.
    """
    posts = spark.read.parquet(f"{silver_path}/posts")

    # Explode hashtags (1 row per hashtag per post)
    exploded = (
        posts
        .filter(F.col("is_spam") == False)  # noqa: E712
        .withColumn("hashtag", F.explode(F.col("hashtags")))
        .withColumn("date", F.to_date(F.col("created_at")))
    )

    trends = (
        exploded
        .groupBy("date", "hashtag")
        .agg(
            F.count("*").alias("post_count"),
            F.countDistinct("user_id").alias("unique_users"),
        )
        .withColumn("rank", F.row_number().over(
            Window.partitionBy("date").orderBy(F.col("post_count").desc())
        ))
    )

    trends.write.parquet(output_path, mode="overwrite")
    print(f"Gold hashtag_trends: {trends.count()} rows → {output_path}")
    return trends


# ========================================================
# 4. SPAM FEATURES (para modelo ML)
# ========================================================

def gold_spam_features(spark: SparkSession, silver_path: str, output_path: str):
    """
    Features para entrenar un modelo de detección de spam:
    - posts_count, posts_per_day
    - avg_text_length
    - unique_texts_ratio (textos únicos / total posts)
    - hashtags_per_post
    - likes_received, likes_given
    - followers_count, following_count
    - follow_ratio (following/followers)
    - label: is_spam (de silver users)
    """
    users = spark.read.parquet(f"{silver_path}/users")
    posts = spark.read.parquet(f"{silver_path}/posts")
    likes = spark.read.parquet(f"{silver_path}/likes")
    follows = spark.read.parquet(f"{silver_path}/follows")

    # Post features per user
    post_features = posts.groupBy("user_id").agg(
        F.count("*").alias("posts_count"),
        F.avg(F.length(F.col("text"))).alias("avg_text_length"),
        F.countDistinct("text").alias("unique_texts"),
        F.avg(F.size(F.col("hashtags"))).alias("avg_hashtags_per_post"),
        F.min("created_at").alias("first_post"),
        F.max("created_at").alias("last_post"),
    )

    post_features = post_features.withColumn(
        "unique_texts_ratio",
        F.when(F.col("posts_count") > 0,
               F.col("unique_texts") / F.col("posts_count"))
        .otherwise(1.0)
    ).withColumn(
        "days_active",
        F.when(F.col("first_post").isNotNull(),
               F.greatest(F.datediff(F.col("last_post"), F.col("first_post")), F.lit(1)))
        .otherwise(1)
    ).withColumn(
        "posts_per_day",
        F.col("posts_count") / F.col("days_active")
    ).drop("unique_texts", "first_post", "last_post")

    # Likes
    likes_given = likes.groupBy("user_id").agg(F.count("*").alias("likes_given"))
    post_user = posts.select("_id", "user_id")
    likes_received = (
        likes.join(post_user, likes.post_id == post_user._id, "inner")
        .groupBy(post_user.user_id.alias("author_id"))
        .agg(F.count("*").alias("likes_received"))
    )

    # Follows
    followers_count = follows.groupBy("following_id").agg(F.count("*").alias("followers_count"))
    following_count = follows.groupBy("follower_id").agg(F.count("*").alias("following_count"))

    # Assemble
    features = (
        users.select("_id", "username", "is_spam")
        .join(post_features, users._id == post_features.user_id, "left").drop("user_id")
        .join(likes_given, users._id == likes_given.user_id, "left").drop("user_id")
        .join(likes_received, users._id == likes_received.author_id, "left").drop("author_id")
        .join(followers_count, users._id == followers_count.following_id, "left").drop("following_id")
        .join(following_count, users._id == following_count.follower_id, "left").drop("follower_id")
        .fillna(0)
    )

    features = features.withColumn(
        "follow_ratio",
        F.when(F.col("followers_count") > 0,
               F.col("following_count") / F.col("followers_count"))
        .otherwise(F.col("following_count"))
    )

    # Rename is_spam → label
    features = features.withColumn("label", F.col("is_spam").cast("integer")).drop("is_spam")

    features.write.parquet(output_path, mode="overwrite")
    print(f"Gold spam_features: {features.count()} rows → {output_path}")
    return features


# ========================================================
# 5. COMMUNITY EDGES (para Neo4j)
# ========================================================

def gold_community_edges(spark: SparkSession, silver_path: str, output_path: str):
    """
    Aristas para cargar en Neo4j:
    - follows (follower_id, following_id)
    - shared hashtags (dos usuarios que usan el mismo hashtag → peso)
    """
    follows = spark.read.parquet(f"{silver_path}/follows")
    posts = spark.read.parquet(f"{silver_path}/posts")

    # Follow edges
    follow_edges = follows.select(
        F.col("follower_id").alias("source"),
        F.col("following_id").alias("target"),
        F.lit("FOLLOWS").alias("type"),
        F.lit(1.0).alias("weight"),
    )

    # Shared hashtag edges (users who post same hashtags)
    user_hashtags = (
        posts
        .filter(F.col("is_spam") == False)  # noqa: E712
        .withColumn("hashtag", F.explode(F.col("hashtags")))
        .select("user_id", "hashtag")
        .distinct()
    )

    shared = (
        user_hashtags.alias("a")
        .join(user_hashtags.alias("b"),
              (F.col("a.hashtag") == F.col("b.hashtag")) &
              (F.col("a.user_id") < F.col("b.user_id")))
        .groupBy(F.col("a.user_id").alias("source"), F.col("b.user_id").alias("target"))
        .agg(F.count("*").alias("weight"))
        .withColumn("type", F.lit("SHARED_INTEREST"))
    )

    edges = follow_edges.unionByName(shared)

    edges.write.parquet(output_path, mode="overwrite")
    print(f"Gold community_edges: {edges.count()} rows → {output_path}")
    return edges


# ========================================================
# RUN ALL GOLD
# ========================================================

def run_gold(spark: SparkSession, silver_path: str, gold_path: str):
    """Ejecuta todo el pipeline silver → gold."""
    print("=" * 60)
    print("GOLD PIPELINE: Silver → Gold")
    print("=" * 60)

    gold_user_stats(spark, silver_path, f"{gold_path}/user_stats")
    gold_post_rankings(spark, silver_path, f"{gold_path}/post_rankings")
    gold_hashtag_trends(spark, silver_path, f"{gold_path}/hashtag_trends")
    gold_spam_features(spark, silver_path, f"{gold_path}/spam_features")
    gold_community_edges(spark, silver_path, f"{gold_path}/community_edges")

    print("\nGold pipeline complete!")
