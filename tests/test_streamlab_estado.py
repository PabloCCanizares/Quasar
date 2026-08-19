"""Tests del bloque STATE de StreamLab.

Se prueba la lógica determinista —qué cuenta como duplicado, qué agrega la
ventana— sobre datos estáticos. Lo que depende de checkpoints y reanudación
no se testea aquí: son ejecuciones lentas cuyo comportamiento ya garantiza
Spark, y lo que hay que fijar es la decisión, no el motor.

Requieren pyspark + Java. Sin ellos el módulo entero se salta.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("pyspark")
from pyspark.sql import SparkSession  # noqa: E402
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
             .appName("quasar-estado-tests")
             .config("spark.sql.shuffle.partitions", "1")
             .config("spark.ui.enabled", "false").getOrCreate())
    except Exception as exc:
        pytest.skip(f"No se pudo arrancar Spark (¿falta Java?): {exc}")
        return
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


@pytest.fixture(scope="module")
def estado():
    ruta = ROOT / "apps" / "streamlab" / "src" / "web" / "routes" / "state.py"
    if not ruta.exists():
        pytest.skip("state.py no está en esta copia (distribución sin soluciones)")
    spec = importlib.util.spec_from_file_location("quasar_estado", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _t(minuto: int) -> datetime:
    return datetime(2026, 8, 9, 10, minuto, 0)


@pytest.fixture(scope="module")
def df(spark):
    """Lecturas con un reintento y una medición distinta del mismo robot.

    RBT-A minuto 0 aparece dos veces (intento 1 y 2): es el mismo dato.
    RBT-A minuto 1 es otra medición: no se debe tocar.
    RBT-B comparte minuto con RBT-A: tampoco es duplicado.
    """
    filas = [
        ("RBT-A", "Lyon", "temperatura", 60.0, _t(0), 1),
        ("RBT-A", "Lyon", "temperatura", 60.0, _t(0), 2),   # reenvío
        ("RBT-A", "Lyon", "temperatura", 61.0, _t(1), 1),
        ("RBT-B", "Lyon", "temperatura", 55.0, _t(0), 1),
        ("RBT-A", "Lyon", "bateria", 90.0, _t(0), 1),       # otro sensor
    ]
    return spark.createDataFrame(filas, ESQUEMA)


# ============================================================
# STATE-1 — deduplicación
# ============================================================

def test_el_reintento_desaparece_y_lo_demas_no(estado, df):
    r = estado.deduplicar(df).collect()
    assert len(r) == 4, "solo sobra la copia de (RBT-A, temperatura, minuto 0)"
    claves = {(x["robot_id"], x["sensor"], x["ts_evento"]) for x in r}
    assert len(claves) == 4


def test_no_confunde_dos_mediciones_distintas_del_mismo_robot(estado, df):
    r = estado.deduplicar(df).collect()
    momentos = sorted(x["ts_evento"] for x in r
                      if x["robot_id"] == "RBT-A" and x["sensor"] == "temperatura")
    assert momentos == [_t(0), _t(1)], "el minuto 1 es otra medición, no una copia"


def test_no_confunde_dos_robots_en_el_mismo_instante(estado, df):
    r = estado.deduplicar(df).collect()
    robots = {x["robot_id"] for x in r
              if x["sensor"] == "temperatura" and x["ts_evento"] == _t(0)}
    assert robots == {"RBT-A", "RBT-B"}


def test_no_confunde_dos_sensores_del_mismo_robot(estado, df):
    r = estado.deduplicar(df).collect()
    sensores = {x["sensor"] for x in r
                if x["robot_id"] == "RBT-A" and x["ts_evento"] == _t(0)}
    assert sensores == {"temperatura", "bateria"}


def test_deduplicar_es_idempotente(estado, df):
    """Aplicarlo dos veces no quita nada más: ya no queda ningún duplicado."""
    una = estado.deduplicar(df).count()
    dos = estado.deduplicar(estado.deduplicar(df)).count()
    assert una == dos


# ============================================================
# STATE-2 — la agregación que se lleva al estado
# ============================================================

def test_el_agregado_solo_mira_temperatura(estado, df):
    r = estado.agregado_por_ventana(df, ventana_min=5).collect()
    total = sum(x["lecturas"] for x in r)
    assert total == 4, "las 4 de temperatura; la de batería queda fuera"


def test_el_agregado_separa_por_robot(estado, df):
    r = estado.agregado_por_ventana(df, ventana_min=5).collect()
    robots = {x["robot_id"] for x in r}
    assert robots == {"RBT-A", "RBT-B"}


def test_deduplicar_antes_de_agregar_cambia_la_cuenta(estado, df):
    """El motivo de todo el bloque: contar duplicados infla el resultado."""
    sin_dedup = sum(x["lecturas"] for x in
                    estado.agregado_por_ventana(df, 5).collect())
    con_dedup = sum(x["lecturas"] for x in
                    estado.agregado_por_ventana(estado.deduplicar(df), 5).collect())
    assert sin_dedup == 4
    assert con_dedup == 3, "sin deduplicar, el reenvío cuenta dos veces"
