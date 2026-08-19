"""Bloque LATE — scaffolds (versión alumno).

Qué hacer con lo que llega tarde.

  LATE-1  retraso        medir cuánto tarda cada lectura en llegar
  LATE-2  descartadas    qué dejaría fuera un watermark dado (en tabla)
  LATE-3  con_watermark  el stream con watermark: cierra ventanas y descarta
  LATE-4  sin_watermark  el mismo stream sin watermark: nada se cierra nunca
  LATE-5  comparar       los dos, lado a lado
  LATE-6  barrido        cuánto esperas frente a cuánto pierdes

La idea de fondo: un flujo no termina nunca, así que si quieres cerrar una
ventana y dar una respuesta, tienes que decidir hasta cuándo esperas. Esa
decisión es el watermark, y no es gratis: lo que llegue después se descarta.

Ojo con una cosa que sorprende: el watermark no actúa solo. Una lectura tres
minutos tardía cae en una ventana que, si es de cinco minutos, todavía está
abierta, así que se acepta. Solo se descarta cuando su ventana ya se cerró.
Ventana y watermark se eligen juntos.

Flujo de trabajo:
  1. Implementa las funciones aquí.
  2. ./lab.sh streamlab restart
  3. Recarga la pestaña Tardíos.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pyspark.sql import DataFrame

router = APIRouter(prefix="/api/streamlab/late", tags=["streamlab-late"])


def _ph(ejercicio: str, pista: str) -> dict:
    return {"error": "scaffold", "exercise": ejercicio, "hint": pista, "available": False}


# ============================================================
# Medir el retraso
# ============================================================

def con_lote_de_llegada(df: DataFrame) -> DataFrame:
    """Añade `lote`: el número de lote en que llegó cada lectura.

    El dato solo dice cuándo se MIDIÓ. Cuándo LLEGÓ está en el nombre del
    fichero que lo trajo.

    Pistas:
      - F.input_file_name() da la ruta del fichero de cada fila.
      - F.regexp_extract(ruta, r"lote-(\\d+)", 1).cast("int") saca el número.
      - Funciona igual en tabla y en flujo.
    """
    raise NotImplementedError("LATE-1a: saca el lote de llegada del nombre del fichero")


def con_retraso(df: DataFrame) -> DataFrame:
    """Añade `retraso_min`: minutos entre medir y llegar.

    Devuelve también `min_evento` (minuto de la jornada en que se midió).

    Pistas:
      - Coge el mínimo ts_evento como referencia del inicio de la jornada.
      - min_evento = (ts_evento - base) / 60, en entero.
      - retraso_min = lote - min_evento (un lote = un minuto de jornada).
    """
    raise NotImplementedError("LATE-1b: calcula el retraso de cada lectura")


def descartadas_por_watermark(df: DataFrame, watermark_min: int,
                              ventana_min: int) -> DataFrame:
    """EJERCICIO LATE-2 — Qué lecturas dejaría fuera este watermark.

    Añade una columna `descartada` (booleana) aplicando la regla de Spark:

        una lectura se descarta si el final de SU ventana quedó por detrás
        del watermark que había cuando llegó.

    Dos detalles que hay que copiar bien o los números no se parecen en nada:

      1. Las ventanas de Spark se alinean a fronteras absolutas de tiempo
         (13:46:00, 13:48:00…), NO al primer dato que tú hayas visto. Calcula
         el corte sobre el epoch: (floor(epoch / seg_ventana) + 1) * seg_ventana.
      2. El watermark va una tanda por detrás: en el lote N se usa el máximo
         visto hasta el lote N−1. Spark no adivina el máximo del lote que
         está procesando.

    Aun así te saldrá una estimación, no el número exacto: el watermark real
    avanza con el máximo observado y la deriva de reloj lo mueve unos
    segundos. En LATE-5 verás los dos números juntos.

    Compruébalo:
      - Con un watermark generoso no deberia descartarse practicamente nada.
      - Cuanto mas apretado el watermark, mas lecturas fuera: la relacion
        tiene que ser monotona. Si al esperar mas pierdes mas, hay un signo
        cambiado.
      - Solo pueden caer lecturas cuya ventana ya estuviese cerrada: si te
        salen descartes con retraso 0, algo no cuadra.
    """
    raise NotImplementedError("LATE-2: marca qué lecturas quedarían fuera")


# ============================================================
# Los streams
# ============================================================

def _agregacion(df: DataFrame, ventana_min: int, watermark_min: int | None) -> DataFrame:
    """Cuenta lecturas por ventana, con watermark o sin él.

    Devuelve: inicio, fin, lecturas, temp_max.

    Pistas:
      - Filtra por sensor temperatura.
      - Si watermark_min no es None: .withWatermark("ts_evento", f"{n} minutes")
        ANTES del groupBy.
      - Agrupa con F.window("ts_evento", f"{ventana_min} minutes").
    """
    raise NotImplementedError("LATE-3a: monta la agregación con y sin watermark")


# ============================================================
# Endpoints
# ============================================================

@router.get("/retraso")
async def retraso() -> dict:
    return _ph("LATE-1", "Implementa con_lote_de_llegada() y con_retraso()")


@router.get("/descartadas")
async def descartadas(watermark: int = Query(2, ge=0, le=15),
                      ventana: int = Query(2, ge=1, le=15)) -> dict:
    return _ph("LATE-2", "Implementa descartadas_por_watermark()")


@router.get("/con_watermark")
async def con_watermark(watermark: int = Query(0, ge=0, le=15),
                        ventana: int = Query(2, ge=1, le=15),
                        lotes_por_tanda: int = Query(1, ge=1, le=30)) -> dict:
    """EJERCICIO LATE-3 — El stream con watermark.

    Ejecuta _agregacion() sobre leer_flujo() con outputMode "append" y
    trigger(availableNow=True). Recoge de recentProgress:
      - numRowsDroppedByWatermark (dentro de stateOperators)
      - numRowsTotal, que es el estado retenido
      - eventTime.watermark, la posición del watermark

    Compruébalo:
      - En modo append solo se emiten ventanas ya cerradas, asi que veras
        menos que ventanas hay en total: es lo esperado.
      - El estado retenido tiene que subir y luego bajar segun el watermark
        cierra ventanas.
      - Usa lotes_por_tanda=1: con tandas grandes los tardios caben dentro de
        la misma tanda y no se descarta nada.
    """
    return _ph("LATE-3", "Ejecuta la agregación con watermark en modo append")


@router.get("/sin_watermark")
async def sin_watermark(ventana: int = Query(2, ge=1, le=15),
                        lotes_por_tanda: int = Query(1, ge=1, le=30)) -> dict:
    """EJERCICIO LATE-4 — El mismo stream, sin watermark.

    Sin watermark Spark no admite "append" (no sabe cuándo una ventana está
    terminada): tienes que usar "complete". Fíjate en numRowsTotal: sin
    watermark el estado no se libera nunca.

    Compruébalo:
      - Sin watermark no se descarta ni una lectura, pero tampoco se libera
        estado: numRowsTotal solo crece.
      - Compara ese estado final con el de LATE-3: ahi esta el coste de no
        cerrar nunca.
      - Si Spark te rechaza el modo append, es justo la leccion: sin
        watermark no sabe cuando una ventana esta terminada.
    """
    return _ph("LATE-4", "Ejecuta la misma agregación sin watermark, modo complete")


@router.get("/comparar")
async def comparar(watermark: int = Query(0, ge=0, le=15),
                   ventana: int = Query(2, ge=1, le=15)) -> dict:
    """EJERCICIO LATE-5 — Con y sin watermark, lado a lado.

    Lo que tiene que quedar claro al mirarlo: con watermark las ventanas se
    cierran y el estado se libera, a cambio de perder lo que llega demasiado
    tarde. Sin él no se pierde nada, pero nada se da nunca por terminado y el
    estado crece sin parar.

    Compruébalo:
      - Con watermark: menos ventanas emitidas, algo descartado, y estado
        liberado. Sin el: todo retenido y nada perdido. Si no ves esa
        diferencia, alguno de los dos no esta configurado como crees.
      - Tu estimacion de LATE-2 y el numero real de Spark no van a coincidir
        del todo, y esta bien: el watermark real avanza con el maximo
        observado y la deriva de reloj lo mueve.
    """
    return _ph("LATE-5", "Ejecuta los dos streams y compara ventanas y estado")


@router.get("/barrido")
async def barrido(ventana: int = Query(2, ge=1, le=15)) -> dict:
    """EJERCICIO LATE-6 — La curva de la decisión: esperar frente a perder.

    Aplica tu descartadas_por_watermark() con varios watermarks (0, 1, 2, 3,
    5, 8, 10) y devuelve cuántas lecturas se pierden con cada uno. Hazlo en
    tabla, no lanzando un stream por cada punto.

    El resultado es una curva que baja: cuanto más esperas, menos pierdes y
    más tardas en responder. Dónde cortarla no lo decide Spark.

    Compruébalo:
      - La curva tiene que bajar: esperar mas nunca puede perder mas.
      - A partir de cierto watermark las perdidas llegan a cero, y ese punto
        deberia parecerse al retraso maximo que mediste en LATE-1.
      - Prueba a cambiar el tamano de ventana: la curva se mueve. El
        watermark no decide solo.
    """
    return _ph("LATE-6", "Barre varios watermarks y devuelve cuánto se pierde con cada uno")
