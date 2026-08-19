"""Tests del bloque LATE de StreamLab.

Se prueban las funciones deterministas (medir retraso, decidir qué queda
fuera de un watermark) sobre datos estáticos. Las que lanzan streams no se
testean aquí: son lentas y su comportamiento ya lo cubre el propio Spark;
lo que hay que fijar es la lógica que decide.

Requieren pyspark + Java. Sin ellos el módulo entero se salta.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("pyspark")
from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

ROOT = Path(__file__).resolve().parent.parent

ESQUEMA = StructType([
    StructField("robot_id", StringType()),
    StructField("almacen", StringType()),
    StructField("sensor", StringType()),
    StructField("valor", DoubleType()),
    StructField("ts_evento", TimestampType()),
    StructField("intento", IntegerType()),
])


@pytest.fixture(scope="module")
def spark():
    try:
        s = (SparkSession.builder.master("local[1]")
             .appName("quasar-tardios-tests")
             .config("spark.sql.shuffle.partitions", "1")
             .config("spark.ui.enabled", "false").getOrCreate())
    except Exception as exc:
        pytest.skip(f"No se pudo arrancar Spark (¿falta Java?): {exc}")
        return
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


@pytest.fixture(scope="module")
def late():
    ruta = ROOT / "apps" / "streamlab" / "src" / "web" / "routes" / "late.py"
    if not ruta.exists():
        pytest.skip("late.py no está en esta copia (distribución sin soluciones)")
    spec = importlib.util.spec_from_file_location("quasar_late", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def buzon(tmp_path_factory, spark):
    """Escribe lotes de verdad: `input_file_name` necesita ficheros reales.

    Cuatro lotes. RBT-PUNTUAL emite y llega a su hora; RBT-TARDE mide en el
    minuto 0 pero su lectura no aparece hasta el lote 3.
    """
    import json
    destino = tmp_path_factory.mktemp("buzon")
    lotes = {
        0: [("RBT-PUNTUAL", 0), ("RBT-TARDE", 0)],   # el tardío aún no llega
        1: [("RBT-PUNTUAL", 1)],
        2: [("RBT-PUNTUAL", 2)],
        3: [("RBT-PUNTUAL", 3)],
    }
    # Quitamos el tardío del lote 0 y lo movemos al 3.
    lotes[0] = [("RBT-PUNTUAL", 0)]
    lotes[3].append(("RBT-TARDE", 0))

    for i, lecturas in lotes.items():
        with open(destino / f"lote-{i:04d}.json", "w", encoding="utf-8") as f:
            for robot, minuto in lecturas:
                f.write(json.dumps({
                    "robot_id": robot,
                    "almacen": "Rotterdam" if robot == "RBT-TARDE" else "Lyon",
                    "sensor": "temperatura",
                    "valor": 60.0,
                    "ts_evento": f"2026-08-09T10:{minuto:02d}:00Z",
                    "intento": 1,
                }) + "\n")
    return destino


@pytest.fixture(scope="module")
def df(spark, buzon):
    from pyspark.sql.types import StructType as ST
    esquema_txt = ST([
        StructField("robot_id", StringType()),
        StructField("almacen", StringType()),
        StructField("sensor", StringType()),
        StructField("valor", DoubleType()),
        StructField("ts_evento", StringType()),
        StructField("intento", IntegerType()),
    ])
    return (spark.read.schema(esquema_txt).json(f"{buzon}/lote-*.json")
            .withColumn("ts_evento", F.to_timestamp("ts_evento")))


# ============================================================
# LATE-1 — medir el retraso
# ============================================================

def test_el_lote_de_llegada_sale_del_nombre_del_fichero(late, df):
    r = late.con_lote_de_llegada(df).collect()
    lotes = sorted({x["lote"] for x in r})
    assert lotes == [0, 1, 2, 3]


def test_el_retraso_distingue_al_que_llega_tarde(late, df):
    r = {(x["robot_id"], x["lote"]): x["retraso_min"]
         for x in late.con_retraso(df).collect()}
    # El puntual mide en el minuto N y llega en el lote N: retraso 0.
    assert r[("RBT-PUNTUAL", 0)] == 0
    assert r[("RBT-PUNTUAL", 3)] == 0
    # El tardío midió en el minuto 0 y no llegó hasta el lote 3.
    assert r[("RBT-TARDE", 3)] == 3


# ============================================================
# LATE-2 — qué deja fuera el watermark
# ============================================================

def test_un_watermark_generoso_no_descarta_nada(late, df):
    d = late.descartadas_por_watermark(df, watermark_min=10, ventana_min=2)
    assert d.filter(F.col("descartada")).count() == 0


def test_un_watermark_ajustado_descarta_al_tardio(late, df):
    d = late.descartadas_por_watermark(df, watermark_min=0, ventana_min=2)
    fuera = [x["robot_id"] for x in d.filter(F.col("descartada")).collect()]
    assert fuera == ["RBT-TARDE"], (
        "con watermark 0 y ventanas de 2 min, la lectura del minuto 0 que "
        "llega en el lote 3 cae en una ventana ya cerrada"
    )


def test_cuanto_mas_esperas_menos_pierdes(late, df):
    """La curva de LATE-6 tiene que ser monótona: nunca perder más al esperar más."""
    perdidas = []
    for wm in (0, 1, 2, 3, 5, 10):
        d = late.descartadas_por_watermark(df, watermark_min=wm, ventana_min=2)
        perdidas.append(d.filter(F.col("descartada")).count())
    assert perdidas == sorted(perdidas, reverse=True), (
        f"esperar más nunca puede perder más: {perdidas}"
    )


def test_una_ventana_grande_protege_al_tardio(late, df):
    """El watermark no decide solo: la ventana también.

    La misma lectura tardía se salva si su ventana sigue abierta. Es lo que
    más sorprende del bloque y por eso se fija en un test.
    """
    estrecha = late.descartadas_por_watermark(df, watermark_min=0, ventana_min=2)
    ancha = late.descartadas_por_watermark(df, watermark_min=0, ventana_min=10)
    assert estrecha.filter(F.col("descartada")).count() == 1
    assert ancha.filter(F.col("descartada")).count() == 0
