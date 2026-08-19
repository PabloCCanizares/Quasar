"""Demo culminante: la misma pregunta, en batch y en streaming.

    ¿Cuántos robots están en riesgo térmico ahora mismo?

No es un ejercicio y no se puede bloquear: es el remate del laboratorio, como
el Pipeline Studio de PreproLab o el "corpus sucio vs limpio" de LLM Lab. Por
eso trae su propia implementación y no depende de que los bloques estén
resueltos.

Lo que se ve al ejecutarla:

  - En **batch** la respuesta es exacta, y llega cuando la jornada ha
    terminado. Correcta e inútil, que fue lo que pasó en Rotterdam.
  - En **streaming** hay una respuesta a los pocos segundos, incompleta, que
    se va corrigiendo según llegan las lecturas tardías hasta que el
    watermark la da por cerrada.

Y el remate: las dos respuestas **coinciden**. Lo que cambia es cuándo llegan,
y el precio de la rápida es haber estado un rato equivocada.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Query
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.config import CHECKPOINTS_PATH, TEMP_ALERTA
from src.spark.session import get_spark, leer_flujo, leer_tabla

router = APIRouter(prefix="/api/streamlab/demo", tags=["streamlab-demo"])


def _en_riesgo(df: DataFrame, ventana_min: int, umbral: float,
               watermark_min: int | None = None) -> DataFrame:
    """Robots cuya temperatura máxima supera el umbral en alguna ventana.

    Es la misma función para tabla y para flujo: lo único que cambia es de
    dónde viene `df`. Sin esa propiedad, la comparación de esta demo no
    tendría sentido, porque estaríamos midiendo dos cosas distintas.

    Se descartan las lecturas del sensor descalibrado (1000 °C): si no, un
    sensor roto dispara una alarma que no existe.
    """
    base = df.filter((F.col("sensor") == "temperatura") & (F.col("valor") < 200))
    if watermark_min is not None:
        base = base.withWatermark("ts_evento", f"{watermark_min} minutes")
    return (
        base.groupBy(F.window("ts_evento", f"{ventana_min} minutes"), "robot_id")
        .agg(F.max("valor").alias("temp_max"))
        .filter(F.col("temp_max") >= umbral)
    )


@router.get("/riesgo")
async def riesgo(ventana: int = Query(5, ge=1, le=15),
                 umbral: float = Query(TEMP_ALERTA, ge=0, le=200),
                 watermark: int = Query(2, ge=0, le=15),
                 lotes_por_tanda: int = Query(3, ge=1, le=15)) -> dict:
    """¿Cuántos robots están en riesgo térmico? Respondido de las dos formas."""
    spark = get_spark()

    # --- La respuesta de batch: exacta, y disponible al final ---
    tabla = leer_tabla()
    robots_batch = sorted(
        r["robot_id"] for r in
        _en_riesgo(tabla, ventana, umbral).select("robot_id").distinct().collect()
    )
    lecturas_totales = tabla.filter(F.col("sensor") == "temperatura").count()

    # --- La respuesta de streaming: pronto, y corrigiéndose ---
    # Modo `complete`: cada tanda entrega la agregación completa hasta ese
    # momento, que es justo lo que se quiere enseñar — cómo evoluciona la
    # respuesta, no solo cuál es la final.
    #
    # Efecto secundario que conviene saber: en `complete` Spark tiene que
    # conservar todo el estado para poder reemitirlo, así que no lo libera y
    # el contador de descartes por watermark sale siempre a cero. No es que
    # no haya lecturas tardías —las hay, y el bloque LATE las mide—, es que
    # este modo no descarta. Por eso aquí no se informa de ese número.
    evolucion: list[dict] = []
    sufijo = uuid.uuid4().hex[:8]
    destino = Path(CHECKPOINTS_PATH) / f"tmp_demo_{sufijo}"

    def capturar(lote_df, lote_id):
        robots = sorted(r["robot_id"] for r in
                        lote_df.select("robot_id").distinct().collect())
        previos = set(evolucion[-1]["robots"]) if evolucion else set()
        evolucion.append({
            "tanda": lote_id,
            "robots": robots,
            "n": len(robots),
            "nuevos": sorted(set(robots) - previos),
        })

    try:
        flujo = _en_riesgo(leer_flujo(spark, lotes_por_tanda=lotes_por_tanda),
                           ventana, umbral, watermark_min=watermark)
        consulta = (
            flujo.writeStream.foreachBatch(capturar)
            .outputMode("complete")
            .option("checkpointLocation", str(destino))
            .trigger(availableNow=True).start()
        )
        consulta.awaitTermination(timeout=300)
        progreso = consulta.recentProgress
        consulta.stop()
    finally:
        shutil.rmtree(destino, ignore_errors=True)

    # Cuántos lotes lleva vistos el stream en cada tanda: es la medida de
    # "cuánta jornada había pasado" cuando dio esa respuesta.
    acumulado = 0
    for i, paso in enumerate(evolucion):
        entradas = progreso[i].get("numInputRows", 0) if i < len(progreso) else 0
        acumulado += entradas
        paso["lecturas_vistas"] = acumulado
        paso["minuto_jornada"] = min((i + 1) * lotes_por_tanda, 30)

    final_stream = evolucion[-1]["robots"] if evolucion else []
    coinciden = final_stream == robots_batch

    # Cuándo dio el stream por primera vez una respuesta, y cuándo la acertó.
    primera = next((p for p in evolucion if p["n"] > 0), None)
    acierto = next((p for p in evolucion if p["robots"] == robots_batch), None)

    return {
        "pregunta": "¿Cuántos robots están en riesgo térmico?",
        "parametros": {"ventana_min": ventana, "umbral_c": umbral,
                       "watermark_min": watermark, "lotes_por_tanda": lotes_por_tanda},
        "batch": {
            "robots": robots_batch,
            "n": len(robots_batch),
            "lecturas": lecturas_totales,
            "cuando": "cuando la jornada ha terminado",
        },
        "streaming": {
            "robots": final_stream,
            "n": len(final_stream),
            "tandas": len(evolucion),
            "evolucion": evolucion,
            "primera_respuesta_en_tanda": primera["tanda"] if primera else None,
            "respuesta_correcta_en_tanda": acierto["tanda"] if acierto else None,
            "cuando": "mientras la jornada sigue",
        },
        "coinciden": coinciden,
        "conclusion": _conclusion(coinciden, acierto, evolucion, lotes_por_tanda),
    }


def _conclusion(coinciden: bool, acierto: dict | None, evolucion: list[dict],
                lotes_por_tanda: int) -> str:
    """El texto que resume qué acaba de pasar, con los números de esta ejecución."""
    if not coinciden:
        return (
            "Las respuestas no coinciden: con este watermark el stream deja fuera "
            "lecturas que el batch sí ve, y alguna cambiaba el resultado. Sube el "
            "watermark y vuelve a probar."
        )

    total = len(evolucion) * lotes_por_tanda
    frases = ["Las dos respuestas coinciden."]
    if acierto is not None:
        minuto = min((acierto["tanda"] + 1) * lotes_por_tanda, total)
        frases.append(
            f"El stream ya la tenía completa en el minuto {minuto} de {total}, "
            "con la jornada todavía en marcha, mientras que el batch no podía "
            "decir nada hasta el final."
        )
    frases.append(
        "El precio fue estar un rato con una respuesta incompleta: quien mirase "
        "antes de ese momento habría visto menos robots de los que hay."
    )
    frases.append(
        "Y algo que conviene notar: la respuesta aguanta aunque se aprieten el "
        "watermark y la ventana. Un robot que se sobrecalienta lo hace de forma "
        "sostenida, así que perder alguna de sus lecturas tardías no cambia quién "
        "supera el umbral. Que un dato llegue tarde no significa que importe: "
        "depende de la pregunta que estés haciendo."
    )
    return " ".join(frases)
