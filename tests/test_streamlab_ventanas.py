"""Tests del bloque WINDOWS de StreamLab.

Aquí se ve la ventaja de escribir las ventanas como funciones
DataFrame → DataFrame: se prueban con datos estáticos, escritos a mano, sin
montar un stream. Probar streams en PySpark es incómodo y lento; probar la
lógica que va dentro del stream, no.

Los datos del fixture son diminutos y deliberados: un robot que emite sin
parar, otro que se calla a mitad, y una lectura absurda del sensor
descalibrado. Con eso se puede afirmar el resultado exacto de cada ventana.

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

ESQUEMA_TEST = StructType([
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
        s = (
            SparkSession.builder.master("local[1]")
            .appName("quasar-ventanas-tests")
            .config("spark.sql.shuffle.partitions", "1")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
    except Exception as exc:  # p.ej. no hay Java en el runner
        pytest.skip(f"No se pudo arrancar Spark (¿falta Java?): {exc}")
        return
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


@pytest.fixture(scope="module")
def ventanas():
    """Carga el módulo solución. Si no está (copia de alumnos), se salta."""
    ruta = ROOT / "apps" / "streamlab" / "src" / "web" / "routes" / "windows.py"
    if not ruta.exists():
        pytest.skip("windows.py no está en esta copia (distribución sin soluciones)")
    spec = importlib.util.spec_from_file_location("quasar_ventanas", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _t(minuto: int, segundo: int = 0) -> datetime:
    return datetime(2026, 8, 9, 10, minuto, segundo)


@pytest.fixture(scope="module")
def df(spark):
    """Telemetría mínima y controlada.

    RBT-A emite del minuto 0 al 12 y se calienta al final.
    RBT-B emite del 0 al 2 y se calla (robot averiado).
    RBT-C tiene una lectura del sensor descalibrado.
    """
    filas = []
    for m in range(0, 13):
        temp = 60.0 if m < 10 else 80.0  # a partir del minuto 10 pasa el umbral
        filas.append(("RBT-A", "Lyon", "temperatura", temp, _t(m), 1))
    for m in range(0, 3):
        filas.append(("RBT-B", "Lyon", "temperatura", 55.0, _t(m), 1))
    filas.append(("RBT-C", "Lyon", "temperatura", 1000.0, _t(1), 1))
    # Otro sensor: no debe aparecer cuando se filtra por temperatura.
    filas.append(("RBT-A", "Lyon", "bateria", 90.0, _t(0), 1))
    return spark.createDataFrame(filas, ESQUEMA_TEST)


# ============================================================
# WIN-1 — ventanas fijas
# ============================================================

def test_ventana_fija_reparte_cada_lectura_en_una_sola_ventana(ventanas, df):
    r = ventanas.ventana_fija(df, minutos=5).collect()
    # 13 lecturas de RBT-A (min 0-12) → ventanas [0,5), [5,10), [10,15)
    a = sorted([x for x in r if x["robot_id"] == "RBT-A"], key=lambda x: x["inicio"])
    assert [x["lecturas"] for x in a] == [5, 5, 3]
    assert sum(x["lecturas"] for x in a) == 13, "ninguna lectura se cuenta dos veces"


def test_ventana_fija_ignora_los_otros_sensores(ventanas, df):
    r = ventanas.ventana_fija(df, minutos=5, sensor="temperatura").collect()
    total = sum(x["lecturas"] for x in r)
    # 13 (A) + 3 (B) + 1 (C absurda) = 17; la de batería queda fuera.
    assert total == 17


def test_ventana_fija_calcula_media_y_maximo(ventanas, df):
    r = [x for x in ventanas.ventana_fija(df, minutos=5).collect()
         if x["robot_id"] == "RBT-A"]
    ultima = max(r, key=lambda x: x["inicio"])
    assert ultima["maximo"] == 80.0
    assert ultima["media"] == 80.0


# ============================================================
# WIN-2 — ventanas deslizantes
# ============================================================

def test_ventana_deslizante_cuenta_las_lecturas_mas_de_una_vez(ventanas, df):
    fija = ventanas.ventana_fija(df, minutos=10)
    desl = ventanas.ventana_deslizante(df, minutos=10, paso=5)
    total_fija = sum(x["lecturas"] for x in fija.collect())
    total_desl = sum(x["lecturas"] for x in desl.collect())
    assert total_desl > total_fija, (
        "con ventanas solapadas cada lectura entra en varias, así que el "
        "recuento total tiene que ser mayor"
    )


def test_ventana_deslizante_produce_mas_ventanas_que_la_fija(ventanas, df):
    fija = ventanas.ventana_fija(df, minutos=10).select("inicio").distinct().count()
    desl = ventanas.ventana_deslizante(df, minutos=10, paso=5).select("inicio").distinct().count()
    assert desl >= fija


# ============================================================
# WIN-3 — ventanas de sesión
# ============================================================

def test_la_sesion_del_robot_averiado_termina_antes(ventanas, df):
    r = ventanas.ventana_sesion(df, gap_min=3).collect()
    fin = {x["robot_id"]: x["fin"] for x in r}
    assert fin["RBT-B"] < fin["RBT-A"], (
        "RBT-B deja de emitir en el minuto 2: su sesión debe cerrarse mucho "
        "antes que la de RBT-A, que sigue hasta el 12"
    )


def test_un_robot_continuo_tiene_una_sola_sesion(ventanas, df):
    r = [x for x in ventanas.ventana_sesion(df, gap_min=3).collect()
         if x["robot_id"] == "RBT-A"]
    assert len(r) == 1, "emite cada minuto, así que nunca se abre un hueco"
    assert r[0]["lecturas"] == 13


def test_no_confunde_una_diferencia_pequena_con_un_robot_mudo(ventanas, spark):
    """Cerrar unos segundos antes que otro no es haberse callado.

    Con la deriva de reloj y el retraso de red, los robots vivos no cierran
    su sesión exactamente a la vez. El criterio tiene que mirar el hueco
    real, no cualquier diferencia: si no, media flota parece averiada.
    """
    filas = []
    # Tres robots vivos que terminan con segundos de diferencia.
    for i, seg in enumerate((0, 20, 45)):
        filas += [
            (f"RBT-VIVO{i}", "Lyon", "temperatura", 50.0, _t(m, seg), 1)
            for m in range(0, 10)
        ]
    # Uno que se calla de verdad, seis minutos antes.
    filas += [("RBT-MUDO", "Lyon", "temperatura", 50.0, _t(m), 1) for m in range(0, 4)]
    df2 = spark.createDataFrame(filas, ESQUEMA_TEST)

    r = ventanas.ventana_sesion(df2, gap_min=3).collect()
    fin = {x["robot_id"]: x["fin"] for x in r}
    fin_global = max(fin.values())
    from datetime import timedelta
    mudos = {rid for rid, f in fin.items() if fin_global - f > timedelta(minutes=3)}
    assert mudos == {"RBT-MUDO"}


def test_un_silencio_mayor_que_el_gap_parte_la_sesion(ventanas, spark):
    """Con un hueco real en el tiempo de evento, la sesión se corta en dos."""
    filas = [("RBT-X", "Lyon", "temperatura", 50.0, _t(m), 1) for m in (0, 1, 2)]
    filas += [("RBT-X", "Lyon", "temperatura", 50.0, _t(m), 1) for m in (20, 21)]
    df2 = spark.createDataFrame(filas, ESQUEMA_TEST)
    r = ventanas.ventana_sesion(df2, gap_min=3).collect()
    assert len(r) == 2, "el silencio de 18 minutos abre una sesión nueva"


# ============================================================
# WIN-4 — alertas térmicas
# ============================================================

def test_las_alertas_solo_salen_cuando_se_supera_el_umbral(ventanas, df):
    r = ventanas.alertas_por_ventana(df, minutos=5, umbral=75).collect()
    robots = {x["robot_id"] for x in r}
    assert "RBT-A" in robots, "se calienta a 80 °C a partir del minuto 10"
    assert "RBT-B" not in robots, "nunca pasa de 55 °C"


def test_el_sensor_descalibrado_es_un_falso_positivo_si_no_se_filtra(ventanas, df):
    """La lección de WIN-4: agregar sin limpiar inventa una alarma."""
    con_filtro = {x["robot_id"] for x in
                  ventanas.alertas_por_ventana(df, minutos=5, umbral=75,
                                               descartar_absurdas=True).collect()}
    sin_filtro = {x["robot_id"] for x in
                  ventanas.alertas_por_ventana(df, minutos=5, umbral=75,
                                               descartar_absurdas=False).collect()}
    assert "RBT-C" not in con_filtro
    assert "RBT-C" in sin_filtro
    assert sin_filtro - con_filtro == {"RBT-C"}


# ============================================================
# La garantía que sostiene la demo final
# ============================================================

def test_las_ventanas_usan_tiempo_de_evento_no_de_llegada(ventanas, spark):
    """El resultado no puede depender del orden en que lleguen las filas.

    Es la propiedad que hace que batch y streaming den lo mismo: si esto
    fallara, la demo de la fase 6 no tendría sentido.
    """
    filas = [("RBT-A", "Lyon", "temperatura", 60.0, _t(m), 1) for m in range(0, 10)]
    ordenado = spark.createDataFrame(filas, ESQUEMA_TEST)
    revuelto = spark.createDataFrame(list(reversed(filas)), ESQUEMA_TEST)

    def resumen(d):
        return sorted(
            (x["inicio"], x["lecturas"])
            for x in ventanas.ventana_fija(d, minutos=5).collect()
        )

    assert resumen(ordenado) == resumen(revuelto)
