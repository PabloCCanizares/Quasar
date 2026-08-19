"""Bloque WINDOWS — scaffolds (versión alumno).

Seis ejercicios sobre cómo cortar el eje del tiempo:

  WIN-1  tumbling   ventanas fijas que no se solapan
  WIN-2  sliding    ventanas que se solapan (media móvil)
  WIN-3  session    ventanas que se cierran solas tras un silencio
  WIN-4  alertas    ventana + umbral: quién está en riesgo y cuándo
  WIN-5  comparar   los tres cortes sobre la misma pregunta
  WIN-6  en_flujo   la misma agregación, ejecutada como stream

Todo el trabajo está en las funciones de arriba: reciben un DataFrame y
devuelven otro. Hazlas bien y los endpoints funcionan solos.

Dos reglas que se aplican a los seis:

  - Agrupa siempre por `ts_evento` (cuándo midió el sensor), nunca por
    cuándo llegó la lectura. Si agrupas por hora de llegada, el resultado
    cambia según cómo vaya la red, y eso no es una respuesta.
  - Escribe funciones DataFrame → DataFrame. El mismo código tiene que
    valer para una tabla y para un flujo; en WIN-6 comprobarás que sí.

Flujo de trabajo:
  1. Implementa las funciones aquí.
  2. ./lab.sh streamlab restart
  3. Recarga la pestaña Ventanas.

Lo que necesitas de la API de Spark:
    F.window(col, "5 minutes")              → ventana fija
    F.window(col, "10 minutes", "5 minutes") → ventana deslizante
    F.session_window(col, "3 minutes")       → ventana de sesión
La columna que devuelven tiene .start y .end.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pyspark.sql import DataFrame

from src.config import TEMP_ALERTA

router = APIRouter(prefix="/api/streamlab/windows", tags=["streamlab-windows"])


def _ph(ejercicio: str, pista: str) -> dict:
    return {"error": "scaffold", "exercise": ejercicio, "hint": pista, "available": False}


# ============================================================
# Las funciones de ventana (DataFrame → DataFrame)
# ============================================================

def ventana_fija(df: DataFrame, minutos: int = 5, sensor: str = "temperatura") -> DataFrame:
    """EJERCICIO WIN-1 — Ventanas tumbling: cortes fijos que no se solapan.

    Cada lectura tiene que caer en exactamente una ventana.

    Devuelve un DataFrame con: inicio, fin, robot_id, media, maximo, lecturas.

    Pistas:
      - Filtra primero por el sensor que te piden.
      - groupBy(F.window("ts_evento", f"{minutos} minutes"), "robot_id").
      - Saca inicio y fin con F.col("window.start") y F.col("window.end").

    Compruébalo:
      - Cada lectura tiene que caer en UNA sola ventana: si sumas la columna
        de lecturas de todas las ventanas, tiene que darte el total de
        lecturas de ese sensor. Si te sale mas, algo se esta contando dos
        veces.
      - Las ventanas tienen que ser contiguas y sin huecos.
      - maximo nunca puede ser menor que media.
    """
    raise NotImplementedError("WIN-1: implementa la ventana fija")


def ventana_deslizante(df: DataFrame, minutos: int = 10, paso: int = 5,
                       sensor: str = "temperatura") -> DataFrame:
    """EJERCICIO WIN-2 — Ventanas sliding: se solapan entre sí.

    Con ventana de 10 min y paso de 5, cada lectura cae en DOS ventanas. Eso
    es lo que las hace reaccionar antes, y también lo que multiplica las filas.

    Devuelve: inicio, fin, robot_id, media, lecturas.

    Pistas:
      - F.window(col, "10 minutes", "5 minutes") — el tercer argumento es el paso.

    Compruébalo:
      - Compara el numero de filas con el de WIN-1: tiene que salir mayor,
        porque cada lectura entra en varias ventanas.
      - Con ventana el doble que el paso, la suma de lecturas tiene que ser
        aproximadamente el doble que en WIN-1. Si sale igual, el paso no se
        esta aplicando y tienes ventanas fijas.
      - Las ventanas se solapan: el inicio de una cae dentro de la anterior.
    """
    raise NotImplementedError("WIN-2: implementa la ventana deslizante")


def ventana_sesion(df: DataFrame, gap_min: int = 3, sensor: str = "temperatura") -> DataFrame:
    """EJERCICIO WIN-3 — Ventanas de sesión: duran lo que dure la actividad.

    No tienen tamaño fijo. Si un robot pasa más de `gap_min` minutos sin
    emitir, su sesión se cierra; la siguiente lectura abre otra.

    Aquí es donde se ven los robots averiados: su última sesión termina mucho
    antes que la de los demás y ya no abren ninguna más.

    Devuelve: inicio, fin, robot_id, lecturas, media.

    Pistas:
      - F.session_window("ts_evento", f"{gap_min} minutes").
      - La columna resultante se llama session_window (no window).

    Compruébalo:
      - Un robot que emite sin parar tiene que dar UNA sola sesion. Si te
        salen muchas, el gap es demasiado pequeno.
      - Los robots averiados cierran su ultima sesion mucho antes que el
        resto: esa diferencia es lo que los delata. Contrasta con el
        manifiesto de la emision, que dice cuantos se callaron.
      - Ojo: un corte de red NO parte la sesion, porque la lectura existio
        igual y su ts_evento es continuo. Si te salen muchos mas cortes de
        los esperados, estas agrupando por hora de llegada.
    """
    raise NotImplementedError("WIN-3: implementa la ventana de sesión")


def alertas_por_ventana(df: DataFrame, minutos: int = 5,
                        umbral: float = TEMP_ALERTA,
                        descartar_absurdas: bool = True) -> DataFrame:
    """EJERCICIO WIN-4 — Qué robots pasan del umbral térmico en cada ventana.

    Es la pregunta del centro de control: la que responderá la demo final.

    Devuelve: inicio, fin, robot_id, temp_max — solo de las ventanas que
    superan el umbral.

    Pistas:
      - Quédate con el sensor temperatura y agrega con F.max("valor").
      - Filtra por >= umbral DESPUÉS de agregar.
      - Con descartar_absurdas=True, quita antes las lecturas del sensor
        descalibrado (valores de 1000 °C).

    Compruébalo:
      - Los robots que salgan tienen que coincidir con los que el emisor puso
        en riesgo: el manifiesto lo dice.
      - Prueba con descartar_absurdas en False: apareceran robots de mas, los
        del sensor descalibrado. Esa diferencia es el resultado del ejercicio.
      - Ninguna temp_max puede quedar por debajo del umbral que pediste.
    """
    raise NotImplementedError("WIN-4: implementa las alertas por ventana")


# ============================================================
# Endpoints
# ============================================================

@router.get("/tumbling")
async def tumbling(minutos: int = Query(5, ge=1, le=30),
                   sensor: str = Query("temperatura")) -> dict:
    return _ph("WIN-1", "Implementa ventana_fija() en windows_ex.py")


@router.get("/sliding")
async def sliding(minutos: int = Query(10, ge=2, le=30),
                  paso: int = Query(5, ge=1, le=15),
                  sensor: str = Query("temperatura")) -> dict:
    return _ph("WIN-2", "Implementa ventana_deslizante() en windows_ex.py")


@router.get("/session")
async def session(gap: int = Query(3, ge=1, le=15),
                  sensor: str = Query("temperatura")) -> dict:
    return _ph("WIN-3", "Implementa ventana_sesion() en windows_ex.py")


@router.get("/alertas")
async def alertas(minutos: int = Query(5, ge=1, le=30),
                  umbral: float = Query(TEMP_ALERTA, ge=0, le=1500),
                  descartar_absurdas: bool = Query(True)) -> dict:
    return _ph("WIN-4", "Implementa alertas_por_ventana() en windows_ex.py")


@router.get("/comparar")
async def comparar(minutos: int = Query(5, ge=1, le=30)) -> dict:
    """EJERCICIO WIN-5 — Los tres cortes sobre la misma pregunta.

    Cuando WIN-1, WIN-2 y WIN-3 funcionen, aplica las tres a la misma
    telemetría y compara: cuántas filas y cuántas ventanas salen de cada una.
    Las tres respuestas son correctas y distintas; entender por qué es el
    objetivo del ejercicio.

    Compruébalo:
      - Las tres respuestas son correctas y distintas: no busques que
        coincidan.
      - La deslizante cuenta mas lecturas que la fija; la fija y la de sesion
        cuentan cada lectura una vez, asi que sus totales deberian cuadrar.
      - Si las tres te dan lo mismo, no estas aplicando tres cortes
        distintos.
    """
    return _ph("WIN-5", "Aplica las tres ventanas y compara filas y ventanas")


@router.get("/en_flujo")
async def en_flujo(minutos: int = Query(5, ge=1, le=30),
                   lotes_por_tanda: int = Query(5, ge=1, le=30)) -> dict:
    """EJERCICIO WIN-6 — La misma agregación, ejecutada como flujo.

    Aquí se comprueba la idea de fondo: tu ventana_fija() no necesita ningún
    cambio para funcionar sobre un stream.

    Pistas:
      - leer_flujo() de src.spark.session te da el DataFrame en modo streaming.
      - Pásalo por tu ventana_fija() tal cual.
      - Escribe con .writeStream, formato "memory", outputMode "complete",
        checkpointLocation dentro de CHECKPOINTS_PATH, y
        .trigger(availableNow=True) para que procese lo pendiente y termine.
      - awaitTermination() y luego lee la tabla en memoria con spark.sql().
      - El resultado tiene que coincidir con /tumbling. Si no coincide, algo
        se está agrupando por hora de llegada en vez de por ts_evento.

    Compruébalo:
      - El resultado tiene que coincidir EXACTAMENTE con /tumbling: mismas
        filas y mismas ventanas. Es la comprobacion que importa.
      - Si no coincide, casi siempre es que algo se agrupa por hora de
        llegada en vez de por ts_evento.
      - El numero de tandas tiene que ser el de lotes dividido entre los
        lotes por tanda.
    """
    return _ph("WIN-6", "Ejecuta tu ventana_fija() sobre leer_flujo() con availableNow")
