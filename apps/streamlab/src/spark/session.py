"""Sesión de Spark y lectura del buzón de telemetría.

Esto es infraestructura, no ejercicio: aquí no hay nada que implementar.

Dos detalles que conviene entender antes de tocar los bloques:

**El esquema es obligatorio en streaming.** Al leer una tabla, Spark puede
mirar el fichero y deducir los tipos. Con un flujo no puede: los datos aún
no han llegado. Por eso el esquema se declara a mano y es el mismo para el
modo tabla y el modo flujo, que además garantiza que ambos vean lo mismo.

**La sesión se reutiliza.** Arrancar Spark cuesta varios segundos; crear una
por petición haría la web inusable. Se crea una vez por proceso y se guarda.
"""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from src.config import RAW_PATH

# Esquema de una lectura de telemetría. `ts_evento` entra como texto y se
# convierte a timestamp al leer: es el tiempo de evento, el que importa.
ESQUEMA = StructType([
    StructField("robot_id", StringType(), nullable=False),
    StructField("almacen", StringType(), nullable=False),
    StructField("sensor", StringType(), nullable=False),
    StructField("valor", DoubleType(), nullable=True),
    StructField("ts_evento", StringType(), nullable=False),
    StructField("intento", IntegerType(), nullable=True),
])

_sesion: SparkSession | None = None


def get_spark() -> SparkSession:
    """Devuelve la SparkSession del proceso, creándola la primera vez."""
    global _sesion
    if _sesion is None:
        _sesion = (
            SparkSession.builder
            .master("local[2]")
            .appName("StreamLab")
            # Los datos son pequeños: con las particiones por defecto (200)
            # cada agregación generaría 200 tareas para nada.
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.driver.memory", "1g")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
        _sesion.sparkContext.setLogLevel("ERROR")
    return _sesion


def _tipar(df: DataFrame) -> DataFrame:
    """Convierte ts_evento a timestamp. Igual en tabla y en flujo."""
    return df.withColumn("ts_evento", F.to_timestamp("ts_evento"))


def leer_tabla(spark: SparkSession | None = None, ruta: str | Path | None = None) -> DataFrame:
    """Lee el buzón entero como una tabla: todo lo emitido, de una vez.

    Es la mirada de PreproLab, la del día siguiente. Sirve de referencia
    para comparar contra el resultado en streaming.
    """
    spark = spark or get_spark()
    ruta = str(ruta or RAW_PATH)
    return _tipar(spark.read.schema(ESQUEMA).json(f"{ruta}/lote-*.json"))


def leer_flujo(spark: SparkSession | None = None, ruta: str | Path | None = None,
               lotes_por_tanda: int = 1) -> DataFrame:
    """Lee el buzón como un flujo: los lotes van entrando según aparecen.

    `maxFilesPerTrigger` marca cuántos lotes entra Spark en cada micro-tanda.
    Con 1, el avance se ve lote a lote, que es lo interesante para aprender.
    """
    spark = spark or get_spark()
    ruta = str(ruta or RAW_PATH)
    return _tipar(
        spark.readStream
        .schema(ESQUEMA)
        .option("maxFilesPerTrigger", lotes_por_tanda)
        .json(f"{ruta}/lote-*.json")
    )
