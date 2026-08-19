"""Tests del emisor de telemetría de StreamLab.

Lo que se comprueba aquí es que la suciedad temporal que el laboratorio
promete está de verdad en los datos, y en cantidad suficiente para que los
ejercicios tengan señal. Si el emisor deja de inyectar retrasos o duplicados,
los bloques de ventanas y watermarks se quedan sin material y estos tests lo
avisan antes que un alumno.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

import pytest

emisor = pytest.importorskip("quasar_emisor")


@pytest.fixture(scope="module")
def emision():
    """Una emisión completa en memoria, sin tocar disco."""
    rnd = random.Random(emisor.SEMILLA)
    num_lotes = 30
    inicio = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)
    flota = emisor.construir_flota(rnd, num_lotes)
    por_lote, cuentas = emisor.generar_lecturas(flota, num_lotes, inicio, rnd)
    return {"flota": flota, "por_lote": por_lote, "cuentas": cuentas,
            "num_lotes": num_lotes, "inicio": inicio}


# ============================================================
# Reproducibilidad
# ============================================================

def test_la_emision_es_reproducible():
    """Dos emisiones con la misma semilla dan exactamente lo mismo.

    Sin esto, cada alumno vería números distintos y la demo dejaría de ser
    comparable entre máquinas.
    """
    def una():
        rnd = random.Random(emisor.SEMILLA)
        inicio = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)
        flota = emisor.construir_flota(rnd, 20)
        return emisor.generar_lecturas(flota, 20, inicio, rnd)

    lotes_a, cuentas_a = una()
    lotes_b, cuentas_b = una()
    assert cuentas_a == cuentas_b
    assert [len(v) for v in lotes_a.values()] == [len(v) for v in lotes_b.values()]


# ============================================================
# Los dos tiempos: evento vs llegada
# ============================================================

def test_dentro_de_un_lote_las_lecturas_no_vienen_ordenadas(emision):
    """La red no respeta el orden de medición: es la premisa del laboratorio."""
    desordenados = 0
    for lecturas in emision["por_lote"].values():
        if len(lecturas) < 5:
            continue
        ts = [r["ts_evento"] for r in lecturas]
        if ts != sorted(ts):
            desordenados += 1
    assert desordenados >= 20, "casi todos los lotes deberían venir desordenados"


def test_hay_lecturas_que_llegan_tarde(emision):
    """Sin datos tardíos no hay nada que enseñar sobre watermarks."""
    assert emision["cuentas"]["retrasadas"] > 0
    assert emision["cuentas"]["muy_retrasadas"] > 0, (
        "hacen falta lecturas con retraso grande (cortes de cobertura) "
        "para que el watermark tenga sentido"
    )


def test_el_retraso_de_red_solo_afecta_al_almacen_con_mala_cobertura(emision):
    """El retraso de red es un fenómeno del almacén lento, no ruido aleatorio.

    Los reintentos quedan fuera del test a propósito: un reenvío llega tarde
    en cualquier almacén, porque de eso va reintentar.
    """
    inicio = emision["inicio"]
    for indice, lecturas in emision["por_lote"].items():
        for r in lecturas:
            if r["intento"] > 1:
                continue
            ts = datetime.fromisoformat(r["ts_evento"].replace("Z", "+00:00"))
            minuto = round((ts - inicio).total_seconds() / 60)
            # El reloj desviado puede mover el minuto ±2; miramos retrasos claros.
            if indice - minuto >= 2:
                assert r["almacen"] == emisor.ALMACEN_LENTO


def test_los_reintentos_llegan_tarde_en_cualquier_almacen(emision):
    """Un reenvío se separa de su medición original, venga de donde venga."""
    inicio = emision["inicio"]
    almacenes_con_reintento_tardio = set()
    for indice, lecturas in emision["por_lote"].items():
        for r in lecturas:
            if r["intento"] == 1:
                continue
            ts = datetime.fromisoformat(r["ts_evento"].replace("Z", "+00:00"))
            if indice - round((ts - inicio).total_seconds() / 60) >= 1:
                almacenes_con_reintento_tardio.add(r["almacen"])
    assert len(almacenes_con_reintento_tardio) > 1, (
        "el reintento tardío no debería ser exclusivo de un almacén"
    )


# ============================================================
# Duplicados por reintento
# ============================================================

def test_los_duplicados_repiten_la_clave_pero_cambian_el_intento(emision):
    """El duplicado es la MISMA medición reenviada, no otra distinta.

    Deduplicar por (robot, sensor, ts_evento) tiene que funcionar; si el
    duplicado cambiara el valor, no sería un reintento.
    """
    vistos: dict[tuple, list[dict]] = {}
    for lecturas in emision["por_lote"].values():
        for r in lecturas:
            vistos.setdefault((r["robot_id"], r["sensor"], r["ts_evento"]), []).append(r)

    repetidas = {k: v for k, v in vistos.items() if len(v) > 1}
    assert repetidas, "tiene que haber duplicados que deduplicar"
    for copias in repetidas.values():
        valores = {c["valor"] for c in copias}
        assert len(valores) == 1, "un reintento reenvía la misma medición"
        assert {c["intento"] for c in copias} == {1, 2}


# ============================================================
# Robots que se callan (material de las ventanas de sesión)
# ============================================================

def test_varios_robots_dejan_de_emitir(emision):
    """La ventana de sesión necesita robots que se callen de verdad."""
    activos_por_lote = [
        {r["robot_id"] for r in lecturas}
        for lecturas in emision["por_lote"].values()
    ]
    todos = set().union(*activos_por_lote)
    ultimos = set().union(*activos_por_lote[-3:])
    mudos = todos - ultimos
    assert len(mudos) >= 3, f"solo {len(mudos)} robots mudos: poca señal"


# ============================================================
# La pregunta de la demo tiene respuesta
# ============================================================

def test_hay_robots_que_superan_el_umbral_termico(emision):
    """Sin sobrecalentamiento real, la demo de la fase 6 no tendría respuesta."""
    calientes = {
        r["robot_id"]
        for lecturas in emision["por_lote"].values()
        for r in lecturas
        if r["sensor"] == "temperatura" and r["valor"] >= 75 and r["valor"] < 1000
    }
    assert len(calientes) >= 3


def test_las_lecturas_absurdas_son_reconocibles(emision):
    """El sensor descalibrado marca 1000 °C: distinguible del calor real."""
    absurdas = [
        r for lecturas in emision["por_lote"].values() for r in lecturas
        if r["sensor"] == "temperatura" and r["valor"] >= 1000
    ]
    assert absurdas, "debe haber lecturas imposibles que filtrar"
    assert all(r["valor"] == 1000.0 for r in absurdas)


# ============================================================
# Ventana de observación
# ============================================================

def test_ninguna_lectura_se_amontona_fuera_de_su_lote(emision):
    """Lo que llega después de cerrar la ventana no se escribe.

    Antes se recortaba al último lote y salía un pico que no existe en la
    realidad; ahora simplemente no llega, y se cuenta aparte.
    """
    tamanos = [len(v) for v in emision["por_lote"].values()]
    medio = sum(tamanos) / len(tamanos)
    assert max(tamanos) < medio * 1.9, (
        f"algún lote está muy por encima de la media ({max(tamanos)} vs {medio:.0f})"
    )
    assert emision["cuentas"]["fuera_de_ventana"] > 0


def test_lote_de_llegada_descarta_lo_que_cae_fuera():
    """La función de llegada devuelve None pasada la ventana."""
    robot = {"almacen": emisor.ALMACEN_LENTO, "cortes": [(5, 9)]}
    # Dentro de un corte: espera a que vuelva la cobertura.
    assert emisor.lote_de_llegada(robot, 6, num_lotes=30) == 9
    # Fuera de corte: solo el retraso base.
    assert emisor.lote_de_llegada(robot, 20, num_lotes=30) == 20 + emisor.RETRASO_BASE_LOTES
    # Pasada la ventana: no llega.
    assert emisor.lote_de_llegada(robot, 29, num_lotes=30) is None
    # Un almacén con buena cobertura entrega en su propio lote.
    assert emisor.lote_de_llegada({"almacen": "Lyon", "cortes": []}, 10, 30) == 10
