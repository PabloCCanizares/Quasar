"""
Spark: Carga datos de Silver y Gold a MongoDB.

Usa el conector oficial mongo-spark-connector.

Uso:
    python -m src.spark.load_to_mongo
"""

import os

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from src.config import SPARK_MASTER, SILVER_PATH, GOLD_PATH, MONGO_URI, MONGO_DB, IS_LOCAL


def get_spark_mongo() -> SparkSession:
    if IS_LOCAL:
        java17 = "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
        if os.path.exists(java17):
            os.environ["JAVA_HOME"] = java17

    return (
        SparkSession.builder
        .master(SPARK_MASTER)
        .appName("SocialLab Load to MongoDB")
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0")
        .config("spark.mongodb.write.connection.uri", MONGO_URI)
        .config("spark.mongodb.write.database", MONGO_DB)
        .getOrCreate()
    )


def write_to_mongo(df: DataFrame, collection: str, mode: str = "overwrite"):
    """Escribe un DataFrame a una colección de MongoDB vía Spark."""
    (
        df.write
        .format("mongodb")
        .mode(mode)
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", collection)
        .save()
    )
    print(f"  {collection}: {df.count()} documents written")


def load_users(spark: SparkSession, silver_path: str):
    print("Loading users...")
    df = spark.read.parquet(f"{silver_path}/users")
    df = (
        df
        .withColumnRenamed("_id", "_id")
        .withColumn("avatar_url", F.lit(""))
        .withColumn("group_id", F.lit(None).cast("string"))
        .withColumn("followers_count", F.lit(0))
        .withColumn("following_count", F.lit(0))
        .withColumn("posts_count", F.lit(0))
        .select("_id", "username", "display_name", "email", "bio",
                "avatar_url", "group_id", "origin", "is_spam",
                "followers_count", "following_count", "posts_count", "created_at")
    )
    write_to_mongo(df, "users")
    return df


def load_posts(spark: SparkSession, silver_path: str):
    print("Loading posts (keeping spam labels for the web detector)...")
    df = spark.read.parquet(f"{silver_path}/posts")

    # Get usernames from Mongo users we just loaded
    users = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "users")
        .load()
        .select(F.col("_id").alias("uid"), F.col("username"))
    )

    df = (
        df
        .join(users, df.user_id == users.uid, "inner")
        .drop("uid")
        .withColumn("mentions", F.array())
        .withColumn("likes_count", F.lit(0))
        .withColumn("group_id", F.lit(None).cast("string"))
        .select("_id", "user_id", "username", "text", "hashtags",
                "mentions", "likes_count", "origin", "group_id", "is_spam", "created_at")
    )
    write_to_mongo(df, "posts")

    # Calculate posts_count per user and update users before follows/Neo4j load.
    print("  Calculating posts_count per user...")
    post_counts = df.groupBy("user_id").agg(F.count("*").alias("new_posts_count"))
    users_current = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "users")
        .load()
        .drop("posts_count")
    )
    users_updated = (
        users_current
        .join(post_counts, users_current._id == post_counts.user_id, "left")
        .drop("user_id")
        .withColumn("posts_count", F.coalesce(F.col("new_posts_count"), F.lit(0)))
        .drop("new_posts_count")
    )
    write_to_mongo(users_updated, "users")
    return df


def load_likes(spark: SparkSession, silver_path: str):
    print("Loading likes...")
    df = spark.read.parquet(f"{silver_path}/likes")

    # Only valid users and posts
    valid_users = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "users")
        .load()
        .select(F.col("_id").alias("valid_uid"))
    )
    valid_posts = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "posts")
        .load()
        .select(F.col("_id").alias("valid_pid"))
    )

    df = (
        df
        .join(valid_users, df.user_id == valid_users.valid_uid, "inner").drop("valid_uid")
        .join(valid_posts, df.post_id == valid_posts.valid_pid, "inner").drop("valid_pid")
        .select("_id", "user_id", "post_id", "origin", "created_at")
    )
    write_to_mongo(df, "likes")

    # Calculate real likes_count per post and update posts
    print("  Calculating likes_count per post...")
    likes_count = df.groupBy("post_id").agg(F.count("*").alias("likes_count"))

    # Read current posts, update likes_count, rewrite
    posts = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "posts")
        .load()
        .drop("likes_count")
    )
    posts_updated = (
        posts
        .join(likes_count, posts._id == likes_count.post_id, "left")
        .drop("post_id")
        .withColumn("likes_count", F.coalesce(F.col("likes_count"), F.lit(0)))
    )
    write_to_mongo(posts_updated, "posts")
    return df


def load_follows(spark: SparkSession, silver_path: str):
    print("Loading follows...")
    df = spark.read.parquet(f"{silver_path}/follows")

    valid_users = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "users")
        .load()
        .select(F.col("_id").alias("vid"))
    )

    df = (
        df
        .join(valid_users.alias("v1"), df.follower_id == F.col("v1.vid"), "inner")
        .drop(F.col("v1.vid"))
        .join(valid_users.alias("v2"), df.following_id == F.col("v2.vid"), "inner")
        .drop(F.col("v2.vid"))
        .select("_id", "follower_id", "following_id", "origin", "created_at")
    )
    write_to_mongo(df, "follows")

    # Update follower/following counts on users
    print("  Calculating follow counts...")
    followers = df.groupBy("following_id").agg(F.count("*").alias("new_followers"))
    following = df.groupBy("follower_id").agg(F.count("*").alias("new_following"))

    users = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "users")
        .load()
        .drop("followers_count", "following_count")
    )
    users_updated = (
        users
        .join(followers, users._id == followers.following_id, "left").drop("following_id")
        .join(following, users._id == following.follower_id, "left").drop("follower_id")
        .withColumn("followers_count", F.coalesce(F.col("new_followers"), F.lit(0)))
        .withColumn("following_count", F.coalesce(F.col("new_following"), F.lit(0)))
        .drop("new_followers", "new_following")
    )
    write_to_mongo(users_updated, "users")
    return df


def load_hashtag_trends(spark: SparkSession, gold_path: str):
    print("Loading hashtag_trends...")
    df = spark.read.parquet(f"{gold_path}/hashtag_trends")
    df = (
        df
        .withColumn("_id", F.concat(F.lit("ht_"), F.monotonically_increasing_id()))
        .withColumn("date", F.col("date").cast("string"))
    )
    write_to_mongo(df, "hashtag_trends")


def load_user_stats(spark: SparkSession, gold_path: str):
    print("Loading user_stats...")
    df = spark.read.parquet(f"{gold_path}/user_stats")
    write_to_mongo(df, "user_stats")


def main():
    spark = get_spark_mongo()
    spark.sparkContext.setLogLevel("WARN")

    silver = str(SILVER_PATH)
    gold = str(GOLD_PATH)

    print("=" * 50)
    print("SPARK → MONGODB")
    print("=" * 50)

    load_users(spark, silver)
    load_posts(spark, silver)
    load_likes(spark, silver)
    load_follows(spark, silver)
    load_hashtag_trends(spark, gold)
    load_user_stats(spark, gold)

    spark.stop()
    print("\nDone!")


if __name__ == "__main__":
    main()
