# StreamLab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.
> Apps hermanas: [PreproLab](../preprolab/README.md) (la misma flota, en batch), [SocialLab](../sociallab/README.md), [LLM Lab](../llmprep/README.md).

**Laboratorio de procesamiento en tiempo real con Spark Structured Streaming.**

Las otras tres apps son batch: cargan un lote, lo procesan entero y guardan. StreamLab enseña la otra mitad, la de los datos que no paran de llegar, donde no puedes esperar a tenerlo todo ni releer el pasado, y hay que decidir qué haces con lo que llega tarde.

## El escenario

Hasta ahora los robots de la flota volcaban su telemetría una vez al día y el análisis se hacía a la mañana siguiente: eso es PreproLab. Hasta que un robot ardió en el almacén de Rotterdam. El sobrecalentamiento estaba en los datos —se veía venir— pero nadie lo leyó hasta catorce horas después. La respuesta era correcta y llegó tarde, que es otra forma de estar equivocada.

Ahora la dirección quiere un centro de control en vivo. Eso es lo que construye el alumno.

Es la misma flota que ya conoce de PreproLab, así que no gasta energía en entender el dominio: la gasta en entender qué cambia cuando los datos siguen llegando.

## Estado actual: COMPLETA

| Bloque | Contenido | Estado |
|---|---|---|
| **Emisor** | Telemetría en vivo en micro-lotes, con la suciedad temporal inyectada | **Fase 2 OK** |
| `windows` | Ventanas tumbling, sliding y de sesión | **Fase 3 OK** |
| `late` | Watermark: qué se corrige con lo que llega tarde y qué se descarta | **Fase 4 OK** |
| `state` | Agregación incremental, checkpoints y dedup por reintento | **Fase 5 OK** |
| **★ Batch vs streaming** | La misma pregunta en los dos regímenes | **Fase 6 OK** |

## Decisiones de diseño

**Ejecuciones acotadas, no procesos eternos.** Una consulta de streaming corre para siempre, pero toda la plataforma está hecha de trabajos que empiezan y terminan. StreamLab usa `trigger=availableNow`: procesa en micro-lotes lo que haya pendiente y termina. El alumno ve el stream avanzar, el trabajo acaba, y no quedan procesos huérfanos ni hace falta supervisarlos. Ventanas, watermarks y estado se comportan igual, así que no se pierde nada.

**La lógica son funciones DataFrame → DataFrame.** El mismo código vale para una tabla y para un flujo. Eso hace que los tests se puedan escribir sobre DataFrames estáticos (probar streams en PySpark es un suplicio) y que la demo de batch vs streaming sea literalmente la misma función aplicada dos veces.

**Sin broker.** La fuente es una carpeta que Spark vigila. Añadir Kafka o Redpanda aportaría realismo a cambio de un servicio más, más memoria y un modo de fallo nuevo; queda documentado y sin implementar, como los AutoEncoders de PreproLab.

**Sin Neo4j.** Su material son series temporales, no relaciones.

## La suciedad, aquí, es temporal

Donde PreproLab inyecta nulls y outliers, StreamLab inyecta desorden en el tiempo:

| Problema | Qué simula |
|---|---|
| Lecturas desordenadas | La red no garantiza el orden de llegada |
| Retrasos por almacén | Rotterdam tiene mala cobertura y sus lecturas llegan con minutos de retraso |
| Relojes con deriva | Algunos robots tienen el reloj adelantado o atrasado |
| Duplicados por reintento | El robot reenvía si no recibe confirmación (*at-least-once*) |
| Sensores que se callan | Un robot deja de emitir: ¿avería o cobertura? |
| Ráfagas al reconectar | Al recuperar red, vuelca de golpe lo acumulado |
| Lecturas imposibles | El sensor descalibrado de 1000 °C, ya conocido de PreproLab |

### El emisor (fase 2)

```bash
./lab.sh streamlab emit                      # 30 lotes de golpe
./lab.sh streamlab emit --intervalo 2        # uno cada 2 s, para verlo llegar
./lab.sh streamlab emit --lotes 10
```

Escribe `raw/lote-NNNN.json` (JSON Lines) y un manifiesto `raw/_emision.json`. Cada lectura lleva **dos tiempos**: `ts_evento`, cuándo midió el sensor, y el lote en que llega. Que no coincidan es de donde sale todo el laboratorio.

Con la semilla fija (42), una jornada de 30 lotes da:

| | |
|---|---|
| lecturas escritas | 3.508 |
| llegan tarde | 1.233 (69 con más de 3 lotes de retraso) |
| duplicadas por reintento | 127 |
| nunca llegaron | 180 (robots averiados) + 39 (fuera de ventana) |
| lecturas sobre 75 °C | 45 |

El manifiesto guarda esos recuentos como **ground truth**: el alumno comprueba si su detector acierta en vez de creérselo, igual que con los noise filters de PreproLab.

Dos detalles del modelo que importan: lo que llegaría después de cerrar la ventana **no se escribe** (amontonarlo en el último lote crearía un pico que no existe), y los cortes de cobertura de Rotterdam hacen que un robot acumule y **suelte de golpe** varios minutos al recuperar la señal.

### Bloque WINDOWS (fase 3) — detalle

Seis ejercicios sobre cómo cortar el eje del tiempo:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| WIN-1 | `GET /api/streamlab/windows/tumbling?minutos=N` | Ventanas fijas que no se solapan |
| WIN-2 | `GET /api/streamlab/windows/sliding?minutos=N&paso=M` | Ventanas deslizantes |
| WIN-3 | `GET /api/streamlab/windows/session?gap=N` | Ventanas de sesión + detección de robots mudos |
| WIN-4 | `GET /api/streamlab/windows/alertas?descartar_absurdas=` | Riesgo térmico por ventana |
| WIN-5 | `GET /api/streamlab/windows/comparar?minutos=N` | Los tres cortes sobre la misma pregunta |
| WIN-6 | `GET /api/streamlab/windows/en_flujo?lotes_por_tanda=N` | La misma agregación, como stream |

Validado sobre la jornada de 30 lotes:

| Corte | Filas | Ventanas | Lecturas contadas |
|---|---|---|---|
| tumbling 5 min | 267 | 7 | 1.177 |
| sliding 10/5 min | 307 | 8 | **2.354** (exactamente el doble) |
| session gap 3 min | 40 | 3 | 1.177 |

Dos resultados que valen por sí solos:

- **WIN-3 detecta exactamente los 5 robots que el emisor averió** (`RBT-0018, 0020, 0027, 0029, 0038`), contrastado contra el ground truth. Y no le engaña un corte de red: la lectura existió igual, solo llegó tarde, así que su `ts_evento` es continuo y la sesión no se parte. Solo el silencio de verdad la corta.
- **WIN-4 encuentra 5 robots en riesgo con el filtro y 9 sin él.** Los 4 de más son el sensor descalibrado de 1000 °C: agregar sin limpiar inventa alarmas.

Y la garantía que sostiene la demo final: **WIN-6 da exactamente lo mismo que WIN-1** (267 filas, 7 ventanas), con la misma función y solo cambiando la fuente.

#### Dos trampas de Spark que están documentadas en el código

- **`session_window` y el pruning de columnas.** Hacer `df.select("inicio").distinct().count()` sobre una agregación de sesión devuelve las sesiones *sin fusionar* (89 en vez de 3), porque Spark rehace el plan al proyectar. La solución materializa el resultado una vez y cuenta en Python.
- **El checkpoint hace que la segunda ejecución no vea nada.** WIN-6 usa un checkpoint de usar y tirar para poder repetirse; recordar por dónde ibas es justo la lección del bloque `state`, no de este.

### Bloque LATE (fase 4) — detalle

Seis ejercicios sobre qué hacer con lo que llega tarde:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| LATE-1 | `/late/retraso` | Medir el retraso con `input_file_name()` |
| LATE-2 | `/late/descartadas?watermark=&ventana=` | Qué dejaría fuera un watermark (a mano) |
| LATE-3 | `/late/con_watermark` | Stream con watermark, modo `append` |
| LATE-4 | `/late/sin_watermark` | Stream sin watermark, modo `complete` |
| LATE-5 | `/late/comparar` | Los dos, lado a lado |
| LATE-6 | `/late/barrido` | La curva esperar frente a perder |

El retraso medido confirma la narrativa: **Rotterdam tiene 1,21 min de retraso medio y hasta 6**, mientras el resto de almacenes se queda en 0,02–0,06 (solo reintentos).

**La comparación que resume el bloque** (ventanas de 2 min, watermark 0):

| | modo | ventanas | descartadas | estado retenido |
|---|---|---|---|---|
| con watermark | `append` | 15 cerradas | 13 | **2 filas** |
| sin watermark | `complete` | 16 | 0 | **16 filas** |

Con watermark las ventanas se cierran y el estado se libera, a cambio de perder lo que llega demasiado tarde. Sin él no se pierde nada, pero nada se da nunca por terminado y el estado crece sin parar.

Y la curva de LATE-6, sobre 1.177 lecturas con ventanas de 2 min:

| esperar | 0 min | 1 min | 2 min | 3 min | 5 min |
|---|---|---|---|---|---|
| perder | 22 | 11 | 2 | 1 | 0 |

#### Dos cosas que el bloque enseña casi solo

- **El watermark no decide solo: la ventana también.** Una lectura tres minutos tardía cae en una ventana de cinco minutos que *todavía está abierta*, así que se acepta. Solo se descarta cuando su ventana ya se cerró. Por eso LATE-2 y LATE-6 mueven los dos parámetros, y hay un test que fija justo esto.
- **La estimación a mano no cuadra con Spark, y está bien que no cuadre.** LATE-2 da 22 donde Spark descarta 13. Replicar la regla exige copiar dos detalles (las ventanas se alinean a fronteras absolutas de tiempo, y el watermark va una tanda por detrás), y aun así queda diferencia porque el watermark real avanza con el máximo observado y la deriva de reloj lo mueve. LATE-5 enseña los dos números juntos a propósito.

### Bloque STATE (fase 5) — detalle

Seis apartados sobre la memoria del flujo:

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| STATE-1 | `/state/dedup` | Deduplicar por clave con watermark |
| STATE-2 | `/state/incremental` | Ver crecer y liberarse el estado, tanda a tanda |
| STATE-3 | `/state/a_mongo` | Escribir con `foreachBatch` + upsert |
| STATE-4 | `/state/reanudar?reiniciar=` | Con checkpoint fijo: la 2ª pasada no repite |
| STATE-5 | `/state/sin_memoria` | Checkpoint nuevo cada vez: siempre relee todo |
| STATE-6 | `/state/recuperacion` | Demo de caída y reanudación |

Resultados verificados:

- **Dedup exacto**: 3.508 → 3.381, los **127** duplicados que el emisor marcó como reintento. Ni uno más ni uno menos.
- **El estado sube y baja**: 79 → 119 → 70 a lo largo de las tandas, liberando ~40 filas cada vez que el watermark cierra ventanas. Es la razón por la que agregar un flujo infinito cabe en una memoria finita.
- **Reanudar funciona**: 1ª pasada 1.177 lecturas, 2ª pasada **0**. Sin checkpoint estable, siempre 1.177.
- **Recuperación**: 611 + 566 = **1.177**, idéntico a una pasada sin cortes. Ni pierde ni repite.

#### Tres trampas que documenta el código

- **El sink `memory` no sabe reanudar desde checkpoint** (*does not support recovering from checkpoint location*). Como reanudar es justo lo que enseña el bloque, todo va por `foreachBatch`, que sí lo soporta.
- **El checkpoint rastrea los ficheros por ruta.** Si la segunda pasada lee de otra carpeta, Spark no reconoce nada y reprocesa todo. Por eso la demo de recuperación usa la **misma** carpeta y copia dentro los lotes que faltaban, que es como llegan de verdad.
- **Interrumpir una consulta en marcha es mala idea como ejercicio.** El primer intento de simular la caída cortando un `processingTime` trigger dejó la petición colgada diez minutos. Por eso STATE-6 es una demo con dos ejecuciones acotadas, deterministas.

## Arranque rápido

```bash
./lab.sh streamlab up
```

Web: <http://localhost:8003>

```bash
./lab.sh streamlab status     # flags y contenedores
./lab.sh streamlab logs       # seguir el log
./lab.sh streamlab down       # parar solo esta app
```

## Modo laboratorio

Los bloques se abren y se cierran en runtime, desde el [Hub](http://localhost:8080#config) o por terminal:

```bash
./lab.sh streamlab unlock windows
./lab.sh streamlab solutions     # abre todos
./lab.sh streamlab exercises     # todos como ejercicio
```

## Estructura

```text
apps/streamlab/
├── src/
│   ├── config/      # Configuración propia (importa de infra/shared/)
│   ├── web/         # FastAPI + SPA
│   ├── seed/        # Emisor de telemetría en vivo (fase 2)
│   └── spark/       # Consultas de Structured Streaming (fases 3-5)
├── main.py
├── Dockerfile
└── requirements.txt
```

El data lake vive en `infra/data/streamlab/`: `raw/` es el buzón donde el emisor deja micro-lotes y que Spark vigila, y `checkpoints/` es donde Structured Streaming recuerda por dónde iba.

## API expuesta

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | `{"status": "ok", "app": "streamlab"}` |
| `GET /api/streamlab/lab/status` | Bloques desbloqueados según `LAB_STREAMLAB` |

Los endpoints de cada bloque se añaden según avanzan las fases.

### La demo culminante (fase 6) — detalle

`GET /api/streamlab/demo/riesgo` responde **«¿cuántos robots están en riesgo térmico?»** de las dos formas. No es un ejercicio y no se puede bloquear, como el Pipeline Studio de PreproLab.

| | Respuesta | Cuándo |
|---|---|---|
| Batch | 5 robots | cuando la jornada ha terminado |
| Streaming | 5 robots | **en el minuto 24 de 30** |

Y la evolución de la respuesta del stream, tanda a tanda:

| minuto | 3–15 | 18 | 21 | 24 | 27–30 |
|---|---|---|---|---|---|
| robots detectados | 0 | 1 | 4 | **5** | 5 |

Las dos respuestas **coinciden**. Lo que cambia es cuándo llegan: el stream la tuvo completa con la jornada aún en marcha, y el precio fue estar un rato con una respuesta incompleta —quien mirase en el minuto 18 habría visto uno de cinco.

Es la misma función `_en_riesgo()` aplicada a una tabla y a un flujo. Sin esa propiedad la comparación no valdría, porque se estarían midiendo dos cosas distintas.

#### Dos cosas que la demo enseña sin querer

- **La respuesta aguanta aunque se aprieten watermark y ventana.** Probado con ventana 2 y watermark 0: siguen coincidiendo. Un robot que se sobrecalienta lo hace de forma sostenida, así que perder alguna lectura tardía no cambia quién supera el umbral. Que un dato llegue tarde no significa que importe: depende de la pregunta.
- **En modo `complete` el contador de descartes por watermark sale siempre a cero**, porque Spark tiene que conservar todo el estado para reemitirlo y por tanto no evicta nada. No es que no haya tardíos —los hay, y el bloque LATE los mide—, es que ese modo no descarta. Por eso la demo no informa de ese número: habría sido un cero engañoso.
