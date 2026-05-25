"""
Spark: Carga grafo social a Neo4j.

Usa el conector oficial neo4j-spark-connector.
Crea nodos User, Hashtag y relaciones FOLLOWS, INTERESTED_IN.

Uso:
    python -m src.spark.load_to_neo4j
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.config import (
    SILVER_PATH, GOLD_PATH,
    MONGO_URI, MONGO_DB,
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
)
from infra.shared.spark import build_spark


def get_spark_neo4j() -> SparkSession:
    return build_spark(
        "SocialLab Load to Neo4j",
        extra_configs={
            "spark.jars.packages": (
                "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3,"
                "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0"
            ),
        },
    )


def neo4j_opts(df_writer):
    """Aplica opciones comunes de Neo4j a un DataFrameWriter."""
    return (
        df_writer
        .format("org.neo4j.spark.DataSource")
        .option("url", NEO4J_URI)
        .option("authentication.type", "basic")
        .option("authentication.basic.username", NEO4J_USER)
        .option("authentication.basic.password", NEO4J_PASSWORD)
    )


def clean_neo4j(spark: SparkSession):
    """Limpia Neo4j antes de cargar."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (h:Hashtag) REQUIRE h.name IS UNIQUE")
    driver.close()
    print("  Neo4j cleaned and constraints created")


def load_user_nodes(spark: SparkSession):
    """Carga usuarios como nodos :User desde MongoDB."""
    print("Loading User nodes...")
    users = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "users")
        .load()
        .filter(F.col("is_spam") == False)  # noqa: E712
        .select(
            F.col("_id").alias("id"),
            "username", "display_name", "origin",
            "followers_count", "following_count", "posts_count",
        )
    )

    (
        neo4j_opts(users.write)
        .mode("overwrite")
        .option("labels", "User")
        .option("node.keys", "id")
        .save()
    )
    print(f"  {users.count()} User nodes created")


def load_hashtag_nodes(spark: SparkSession):
    """Carga hashtags como nodos :Hashtag desde MongoDB."""
    print("Loading Hashtag nodes...")
    hashtags = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "posts")
        .load()
        .select(F.explode(F.col("hashtags")).alias("name"))
        .filter(F.col("name").isNotNull())
        .filter(F.col("name") != "")
        .distinct()
    )

    (
        neo4j_opts(hashtags.write)
        .mode("overwrite")
        .option("labels", "Hashtag")
        .option("node.keys", "name")
        .save()
    )
    print(f"  {hashtags.count()} Hashtag nodes created")


def load_follows_edges(spark: SparkSession):
    """Carga relaciones FOLLOWS desde MongoDB."""
    print("Loading FOLLOWS edges...")
    follows = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "follows")
        .load()
        .select(
            F.col("follower_id").alias("source.id"),
            F.col("following_id").alias("target.id"),
        )
    )

    (
        neo4j_opts(follows.write)
        .mode("overwrite")
        .option("relationship", "FOLLOWS")
        .option("relationship.save.strategy", "keys")
        .option("relationship.source.labels", "User")
        .option("relationship.source.node.keys", "source.id:id")
        .option("relationship.target.labels", "User")
        .option("relationship.target.node.keys", "target.id:id")
        .save()
    )
    print(f"  {follows.count()} FOLLOWS edges created")


def load_interested_in_edges(spark: SparkSession):
    """Carga relaciones INTERESTED_IN (user → hashtag) desde MongoDB."""
    print("Loading INTERESTED_IN edges...")
    user_tags = (
        spark.read.format("mongodb")
        .option("connection.uri", MONGO_URI)
        .option("database", MONGO_DB)
        .option("collection", "posts")
        .load()
        .filter(F.col("is_spam") == False)  # noqa: E712
        .select("user_id", F.explode(F.col("hashtags")).alias("hashtag"))
        .filter(F.col("hashtag").isNotNull())
        .filter(F.col("hashtag") != "")
        .distinct()
        .select(
            F.col("user_id").alias("source.id"),
            F.col("hashtag").alias("target.name"),
        )
    )

    (
        neo4j_opts(user_tags.write)
        .mode("overwrite")
        .option("relationship", "INTERESTED_IN")
        .option("relationship.save.strategy", "keys")
        .option("relationship.source.labels", "User")
        .option("relationship.source.node.keys", "source.id:id")
        .option("relationship.target.labels", "Hashtag")
        .option("relationship.target.node.keys", "target.name:name")
        .save()
    )
    print(f"  {user_tags.count()} INTERESTED_IN edges created")


def main():
    spark = get_spark_neo4j()
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 50)
    print("SPARK → NEO4J")
    print("=" * 50)

    clean_neo4j(spark)
    load_user_nodes(spark)
    load_hashtag_nodes(spark)
    load_follows_edges(spark)
    load_interested_in_edges(spark)

    # Print summary
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        print("\nNeo4j summary:")
        for r in session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt"):
            print(f"  {r['label']}: {r['cnt']} nodes")
        for r in session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt"):
            print(f"  {r['type']}: {r['cnt']} edges")
    driver.close()

    spark.stop()
    print("\nDone!")


if __name__ == "__main__":
    main()
