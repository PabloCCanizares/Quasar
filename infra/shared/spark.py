"""Constructor de SparkSession compartido.

Cualquier app que necesite Spark llama a `build_spark(app_name, with_connectors=True/False)`.
Maneja la detección de Java en macOS local (Homebrew openjdk@17) y la inclusión
opcional de los conectores de MongoDB y Neo4j.
"""

from __future__ import annotations

import os
from pathlib import Path

from pyspark.sql import SparkSession

from infra.shared.config_base import SPARK_MASTER, IS_LOCAL


# Posibles ubicaciones de Java 17 en macOS (Apple Silicon y x86).
# Se prueban en orden hasta encontrar una válida.
_MAC_JAVA17_CANDIDATES = [
    "/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home",
    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
    "/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
]


def _ensure_java_home() -> None:
    """En macOS local, fija JAVA_HOME si no está y encuentra openjdk@17."""
    if os.getenv("JAVA_HOME"):
        return
    for candidate in _MAC_JAVA17_CANDIDATES:
        if Path(candidate).exists():
            os.environ["JAVA_HOME"] = candidate
            return


def build_spark(app_name: str, with_connectors: bool = False, driver_memory: str = "2g") -> SparkSession:
    """Construye y devuelve una SparkSession.

    Args:
        app_name: nombre que aparece en la UI de Spark.
        with_connectors: si True, añade los paquetes Maven para Mongo y Neo4j.
        driver_memory: memoria del driver (default 2g).
    """
    if IS_LOCAL:
        _ensure_java_home()

    builder = (
        SparkSession.builder
        .master(SPARK_MASTER)
        .appName(app_name)
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .config("spark.driver.memory", driver_memory)
    )

    if with_connectors:
        builder = builder.config(
            "spark.jars.packages",
            "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0,"
            "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3",
        )

    return builder.getOrCreate()
