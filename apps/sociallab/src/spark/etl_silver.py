"""
Spark ETL: Raw → Silver

Resuelve todos los problemas de datos sucios:
  1. Timestamps: 5 formatos → UTC normalizado
  2. Usuarios duplicados: dedup por email
  3. Hashtags: normalizar a minúsculas sin # ni espacios
  4. Encoding roto: Ã¡ → á
  5. Campos faltantes: eliminar registros incompletos
  6. Spam: detectar y marcar (no eliminar — eso es decisión de gold)
  7. Likes huérfanos: eliminar referencias a posts/users inexistentes
  8. Self-follows y ghost follows: eliminar
  9. Likes duplicados: dedup por (user_id, post_id)

Cada función recibe SparkSession + rutas. Mismo código local y Databricks.
"""

import re
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType, TimestampType

# ========================================================
# 1. TIMESTAMP NORMALIZATION
# ========================================================

@F.udf(TimestampType())
def parse_timestamp(ts: str):
    """Parsea 5 formatos de timestamp a datetime UTC."""
    if ts is None:
        return None
    ts = ts.strip()

    # Epoch (e.g. "1711741200")
    if ts.isdigit() and len(ts) >= 10:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    # ISO format (e.g. "2026-03-29T18:30:00+00:00")
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    # US format (e.g. "03/29/2026 06:30 PM")
    try:
        return datetime.strptime(ts, "%m/%d/%Y %I:%M %p").replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # EU format (e.g. "29-03-2026 18:30")
    try:
        return datetime.strptime(ts, "%d-%m-%Y %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Relative (e.g. "hace 3 días", "hace 5 horas")
    match = re.match(r"hace (\d+) (días?|horas?)", ts)
    if match:
        from datetime import timedelta
        amount = int(match.group(1))
        unit = match.group(2)
        now = datetime.now(timezone.utc)
        if "día" in unit:
            return now - timedelta(days=amount)
        elif "hora" in unit:
            return now - timedelta(hours=amount)

    return None


# ========================================================
# 2. ENCODING FIX
# ========================================================

@F.udf(StringType())
def fix_encoding(text: str):
    """Repara encoding roto: Ã¡ → á, etc."""
    if text is None:
        return None
    replacements = {
        "Ã¡": "á", "Ã©": "é", "Ã\xad": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã±": "ñ", "Ã¼": "ü", "Ã\x81": "Á", "Ã\x89": "É",
    }
    for broken, fixed in replacements.items():
        text = text.replace(broken, fixed)
    return text


# ========================================================
# 3. HASHTAG NORMALIZATION
# ========================================================

@F.udf(ArrayType(StringType()))
def normalize_hashtags(tags):
    """Normaliza hashtags: minúsculas, sin #, sin espacios, sin puntos."""
    if tags is None:
        return []
    cleaned = []
    for tag in tags:
        if tag is None:
            continue
        t = tag.strip().lstrip("#").rstrip(".").strip().lower()
        if t and len(t) > 1:
            cleaned.append(t)
    return list(set(cleaned))


# ========================================================
# SILVER: USERS
# ========================================================

def silver_users(spark: SparkSession, input_path: str, output_path: str):
    """
    Raw → Silver users:
    - Fix encoding in display_name, bio
    - Normalize timestamps
    - Drop rows without _id or username
    - Deduplicate by email (keep first)
    """
    df = spark.read.json(input_path)

    df = (
        df
        # Fix encoding
        .withColumn("display_name", fix_encoding(F.col("display_name")))
        .withColumn("bio", fix_encoding(F.col("bio")))
        .withColumn("username", fix_encoding(F.col("username")))
        # Normalize timestamp
        .withColumn("created_at", parse_timestamp(F.col("created_at")))
        # Clean username: lowercase, replace spaces with underscores
        .withColumn("username", F.lower(F.regexp_replace(F.col("username"), r"\s+", "_")))
        # Drop essential nulls
        .filter(F.col("_id").isNotNull())
        .filter(F.col("username").isNotNull())
        .filter(F.col("username") != "")
    )

    # Deduplicate by email (keep first occurrence by _id)
    window = Window.partitionBy("email").orderBy("_id")
    df = (
        df
        .withColumn("_row_num", F.row_number().over(window))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    # Mark spam users
    df = df.withColumn(
        "is_spam",
        F.when(F.col("is_spam") == True, True)  # noqa: E712
        .when(F.upper(F.col("bio")).contains("FOLLOW ME"), True)
        .when(F.upper(F.col("bio")).contains("BEST DEALS"), True)
        .otherwise(False)
    )

    df.write.parquet(output_path, mode="overwrite")
    print(f"Silver users: {df.count()} rows → {output_path}")
    return df


# ========================================================
# SILVER: POSTS
# ========================================================

def silver_posts(spark: SparkSession, input_path: str, output_path: str,
                 valid_user_ids: DataFrame = None):
    """
    Raw → Silver posts:
    - Fix encoding in text
    - Normalize timestamps
    - Normalize hashtags
    - Drop posts without text or user_id
    - Remove orphan posts (user_id not in valid users)
    - Detect spam posts (same text from same user within short window)
    """
    df = spark.read.json(input_path)

    df = (
        df
        .withColumn("text", fix_encoding(F.col("text")))
        .withColumn("created_at", parse_timestamp(F.col("created_at")))
        .withColumn("hashtags", normalize_hashtags(F.col("hashtags")))
        # Drop incomplete
        .filter(F.col("_id").isNotNull())
        .filter(F.col("text").isNotNull())
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("created_at").isNotNull())
    )

    # Remove orphan posts (user doesn't exist)
    if valid_user_ids is not None:
        df = df.join(
            valid_user_ids.select(F.col("_id").alias("_valid_uid")),
            df.user_id == F.col("_valid_uid"),
            "inner"
        ).drop("_valid_uid")

    # Detect spam: same user + same text = spam
    text_window = Window.partitionBy("user_id", "text").orderBy("created_at")
    df = df.withColumn("_text_count", F.count("*").over(text_window))
    df = df.withColumn(
        "is_spam",
        F.when(F.col("_text_count") > 3, True).otherwise(False)
    ).drop("_text_count")

    # Reset likes_count (will be recalculated from actual likes in gold)
    df = df.withColumn("likes_count", F.lit(0))

    df.write.parquet(output_path, mode="overwrite")
    print(f"Silver posts: {df.count()} rows → {output_path}")
    return df


# ========================================================
# SILVER: LIKES
# ========================================================

def silver_likes(spark: SparkSession, input_path: str, output_path: str,
                 valid_user_ids: DataFrame = None, valid_post_ids: DataFrame = None):
    """
    Raw → Silver likes:
    - Normalize timestamps
    - Remove orphan likes (user or post doesn't exist)
    - Deduplicate by (user_id, post_id)
    """
    df = spark.read.json(input_path)

    df = (
        df
        .withColumn("created_at", parse_timestamp(F.col("created_at")))
        .filter(F.col("_id").isNotNull())
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("post_id").isNotNull())
    )

    # Remove orphans
    if valid_user_ids is not None:
        df = df.join(
            valid_user_ids.select(F.col("_id").alias("_valid_uid")),
            df.user_id == F.col("_valid_uid"),
            "inner"
        ).drop("_valid_uid")

    if valid_post_ids is not None:
        df = df.join(
            valid_post_ids.select(F.col("_id").alias("_valid_pid")),
            df.post_id == F.col("_valid_pid"),
            "inner"
        ).drop("_valid_pid")

    # Dedup by (user_id, post_id)
    window = Window.partitionBy("user_id", "post_id").orderBy("created_at")
    df = (
        df
        .withColumn("_row_num", F.row_number().over(window))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    df.write.parquet(output_path, mode="overwrite")
    print(f"Silver likes: {df.count()} rows → {output_path}")
    return df


# ========================================================
# SILVER: FOLLOWS
# ========================================================

def silver_follows(spark: SparkSession, input_path: str, output_path: str,
                   valid_user_ids: DataFrame = None):
    """
    Raw → Silver follows:
    - Normalize timestamps
    - Remove self-follows
    - Remove ghost follows (user doesn't exist)
    - Deduplicate by (follower_id, following_id)
    """
    df = spark.read.json(input_path)

    df = (
        df
        .withColumn("created_at", parse_timestamp(F.col("created_at")))
        .filter(F.col("_id").isNotNull())
        .filter(F.col("follower_id").isNotNull())
        .filter(F.col("following_id").isNotNull())
        # Remove self-follows
        .filter(F.col("follower_id") != F.col("following_id"))
    )

    # Remove ghost follows
    if valid_user_ids is not None:
        valid = valid_user_ids.select(F.col("_id").alias("_vid"))
        df = (
            df
            .join(valid.alias("v1"), df.follower_id == F.col("v1._vid"), "inner")
            .drop(F.col("v1._vid"))
            .join(valid.alias("v2"), df.following_id == F.col("v2._vid"), "inner")
            .drop(F.col("v2._vid"))
        )

    # Dedup
    window = Window.partitionBy("follower_id", "following_id").orderBy("created_at")
    df = (
        df
        .withColumn("_row_num", F.row_number().over(window))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    df.write.parquet(output_path, mode="overwrite")
    print(f"Silver follows: {df.count()} rows → {output_path}")
    return df


# ========================================================
# RUN ALL SILVER
# ========================================================

def run_silver(spark: SparkSession, raw_path: str, silver_path: str):
    """Ejecuta todo el pipeline raw → silver en orden."""
    print("=" * 60)
    print("SILVER PIPELINE: Raw → Silver")
    print("=" * 60)

    # Users first (needed for orphan detection)
    users_df = silver_users(spark, f"{raw_path}/users.json", f"{silver_path}/users")

    # Posts (filter by valid users)
    posts_df = silver_posts(spark, f"{raw_path}/posts.json", f"{silver_path}/posts",
                            valid_user_ids=users_df)

    # Likes (filter by valid users + valid posts)
    silver_likes(spark, f"{raw_path}/likes.json", f"{silver_path}/likes",
                 valid_user_ids=users_df, valid_post_ids=posts_df)

    # Follows (filter by valid users)
    silver_follows(spark, f"{raw_path}/follows.json", f"{silver_path}/follows",
                   valid_user_ids=users_df)

    print("\nSilver pipeline complete!")
