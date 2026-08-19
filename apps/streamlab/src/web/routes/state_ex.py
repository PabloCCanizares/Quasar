"""Bloque STATE — scaffolds (versión alumno).

Un flujo tiene memoria. Cuando agregas por ventana, Spark guarda las cuentas
parciales entre tanda y tanda: eso es el **estado**. Y cuando el proceso se
para, el **checkpoint** es lo que le permite retomar donde iba en vez de
empezar de cero.

  STATE-1  dedup           quitar los duplicados del reintento
  STATE-2  incremental     ver crecer y liberarse el estado, tanda a tanda
  STATE-3  a_mongo         escribir los resultados con foreachBatch
  STATE-4  reanudar        con checkpoint: la segunda pasada no repite trabajo
  STATE-5  sin_memoria     sin checkpoint: cada pasada rehace todo
  STATE-6  recuperacion    qué pasa si el proceso se cae a mitad (demo)

El hilo que une los seis: **entregar una vez y solo una**. El emisor reenvía
cuando no recibe confirmación, así que los duplicados llegan sí o sí;
deduplicar por clave con watermark es lo que los convierte en exactly-once.
Y el checkpoint es lo que evita que un reinicio vuelva a contarlo todo.

Flujo de trabajo:
  1. Implementa las funciones aquí.
  2. ./lab.sh streamlab restart
  3. Recarga la pestaña Estado.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pyspark.sql import DataFrame

router = APIRouter(prefix="/api/streamlab/state", tags=["streamlab-state"])


def _ph(ejercicio: str, pista: str) -> dict:
    return {"error": "scaffold", "exercise": ejercicio, "hint": pista, "available": False}


# ============================================================
# Las funciones
# ============================================================

def deduplicar(df: DataFrame, watermark_min: int = 5) -> DataFrame:
    """EJERCICIO STATE-1 — Quita los reenvíos, dejando una sola copia.

    Pistas:
      - La clave es (robot_id, sensor, ts_evento): un reintento es la MISMA
        medición mandada otra vez.
      - `intento` NO entra en la clave. Es justo lo único que cambia entre la
        original y la copia; si lo incluyes, no deduplicas nada.
      - Pon .withWatermark("ts_evento", ...) ANTES del dropDuplicates. Sin él,
        Spark tendría que recordar todas las claves vistas desde siempre para
        detectar un duplicado, y el estado crecería sin límite.

    Compruébalo:
      - Tienen que desaparecer exactamente tantas filas como lecturas con
        intento > 1 haya en el buzon. Es la comprobacion mas directa.
      - Si desaparece muchisimo mas, has metido `intento` en la clave o te
        falta alguna columna en ella.
      - Aplicarlo dos veces no debe quitar nada nuevo.
    """
    raise NotImplementedError("STATE-1: deduplica por clave con watermark")


def agregado_por_ventana(df: DataFrame, ventana_min: int = 5) -> DataFrame:
    """Temperatura máxima y nº de lecturas por ventana y robot.

    Devuelve: inicio, fin, robot_id, lecturas, temp_max.

    Es la misma idea que ventana_fija() del bloque WINDOWS; si aquel ya te
    funciona, esto es un rato.
    """
    raise NotImplementedError("STATE-2a: agrega por ventana y robot")


# ============================================================
# Endpoints
# ============================================================

@router.get("/dedup")
async def dedup(watermark: int = Query(5, ge=1, le=30)) -> dict:
    return _ph("STATE-1", "Implementa deduplicar() en state_ex.py")


@router.get("/incremental")
async def incremental(ventana: int = Query(5, ge=1, le=15),
                      lotes_por_tanda: int = Query(5, ge=1, le=30)) -> dict:
    """EJERCICIO STATE-2 — Ver crecer y liberarse el estado.

    Ejecuta tu agregado_por_ventana() como flujo (con watermark) y recoge de
    recentProgress, por cada tanda:
      - numInputRows
      - stateOperators[].numRowsTotal   → cuánto estado hay retenido
      - stateOperators[].numRowsRemoved → cuánto se ha liberado

    Lo que tiene que verse: el estado sube mientras hay ventanas abiertas y
    baja cuando el watermark las cierra. Por eso agregar un flujo infinito
    cabe en una memoria finita.

    Compruébalo:
      - El estado tiene que subir mientras hay ventanas abiertas y bajar
        cuando el watermark las cierra. Si solo sube, no hay watermark.
      - La suma de lecturas de todas las tandas tiene que dar el total del
        sensor.
      - Con mas lotes por tanda hay menos tandas, pero el resultado final no
        cambia.
    """
    return _ph("STATE-2", "Ejecuta la agregación como flujo y mira numRowsTotal por tanda")


@router.get("/a_mongo")
async def a_mongo(ventana: int = Query(5, ge=1, le=15)) -> dict:
    """EJERCICIO STATE-3 — Escribir cada tanda a Mongo con foreachBatch.

    foreachBatch te entrega cada micro-tanda como un DataFrame normal, así
    que dentro puedes escribir donde quieras. Es la salida de escape cuando
    no hay conector nativo.

    Pistas:
      - .writeStream.foreachBatch(fn) donde fn(lote_df, lote_id).
      - Dentro, collect() y escribe con pymongo.
      - Usa upsert por (inicio, robot_id), no insert: si una tanda se
        reintenta, tiene que corregir la fila, no duplicarla.

    Compruébalo:
      - Los documentos en Mongo tienen que ser tantos como filas emitio el
        stream, no mas. Si son mas, estas insertando en vez de haciendo
        upsert.
      - Ejecutalo dos veces: el numero de documentos NO debe cambiar. Es la
        prueba de que el upsert funciona.
      - La clave del upsert tiene que identificar la fila de forma unica.
    """
    return _ph("STATE-3", "Escribe con foreachBatch + upsert por (inicio, robot_id)")


@router.get("/reanudar")
async def reanudar(ventana: int = Query(5, ge=1, le=15),
                   reiniciar: bool = Query(False)) -> dict:
    """EJERCICIO STATE-4 — Con checkpoint, la segunda pasada no repite trabajo.

    Ejecuta la consulta con un checkpointLocation FIJO (no uno nuevo cada
    vez). Llama una vez con reiniciar=true y luego otra sin él: la segunda
    debe procesar 0 lecturas.

    Ojo: el sink "memory" NO sabe reanudar desde checkpoint (te dirá "does
    not support recovering from checkpoint location"). Usa foreachBatch.

    Compruébalo:
      - La segunda pasada tiene que procesar 0 lecturas. Si vuelve a leerlo
        todo, el checkpoint no persiste entre llamadas.
      - Si Spark se queja de que la consulta no puede reanudar desde el
        checkpoint, estas usando el sink `memory`: no lo soporta.
      - Borrando el checkpoint tiene que volver a leerlo todo.
    """
    return _ph("STATE-4", "Usa un checkpoint fijo y comprueba que la 2ª pasada lee 0")


@router.get("/sin_memoria")
async def sin_memoria(ventana: int = Query(5, ge=1, le=15)) -> dict:
    """EJERCICIO STATE-5 — Sin checkpoint estable, cada pasada rehace todo.

    Lo mismo que STATE-4 pero con un checkpoint nuevo en cada llamada.
    Compara: aquí siempre se releen los 30 lotes.

    Compruébalo:
      - Aqui SI se relee todo en cada pasada: compara con STATE-4 llamado dos
        veces seguidas y la diferencia tiene que ser evidente.
      - El resultado final es el mismo; lo que cambia es el trabajo repetido.
    """
    return _ph("STATE-5", "Repite STATE-4 con un checkpoint distinto cada vez")


@router.get("/recuperacion")
async def recuperacion(ventana: int = Query(5, ge=1, le=15)) -> dict:
    """DEMO STATE-6 — Qué pasa si el proceso se cae a mitad.

    No es un ejercicio, es una demostración: procesa media jornada, deja que
    "se caiga", y relanza con el mismo checkpoint. El total tiene que salir
    igual que en una pasada sin cortes.

    Un detalle que cuesta ver: las dos pasadas tienen que leer de la MISMA
    carpeta. El checkpoint rastrea los ficheros ya procesados por su ruta, así
    que si la segunda apunta a otro sitio, Spark no reconoce nada y lo
    reprocesa todo.
    """
    return _ph("STATE-6", "Dos pasadas sobre la misma carpeta con el mismo checkpoint")
