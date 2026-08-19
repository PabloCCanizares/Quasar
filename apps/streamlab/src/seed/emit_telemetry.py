"""Emisor de telemetría en vivo de la flota (StreamLab).

Reproduce lo que hacen los robots cuando trabajan: mandar lecturas mientras
la jornada avanza. En vez de un volcado histórico como el de PreproLab, esto
escribe **micro-lotes** en `raw/`, que es la carpeta que Spark vigila.

Cada lote es un fichero JSON Lines. Spark los va recogiendo según aparecen,
igual que recogería mensajes de un broker, pero sin montar un servicio más.

La diferencia clave con una tabla: aquí hay DOS tiempos por lectura.

  ts_evento   cuándo midió el sensor.
  (el lote)   cuándo llegó la lectura al sistema.

Que no coincidan es justo lo que hace difícil el streaming, y de donde salen
los ejercicios de ventanas y watermarks.

Suciedad inyectada, toda de naturaleza temporal:

  1. Desorden          dentro de un lote las lecturas no van ordenadas.
  2. Retraso por red   Rotterdam tiene mala cobertura: sus lecturas llegan
                       varios lotes después de haberse medido.
  3. Relojes con deriva algunos robots van adelantados o atrasados.
  4. Duplicados        el emisor reintenta si no recibe confirmación, así que
                       la misma lectura puede aparecer dos veces.
  5. Sensores mudos    un robot deja de emitir a mitad de jornada.
  6. Ráfagas           al recuperar cobertura, vuelca de golpe lo acumulado.
  7. Lecturas absurdas el sensor descalibrado que marca 1000 °C.

Al terminar escribe `raw/_emision.json` con el recuento real de cada
problema: es el ground truth con el que el alumno comprueba si su detector
funciona, en vez de creérselo.

Uso:
    python -m src.seed.emit_telemetry                    # 30 lotes, sin espera
    python -m src.seed.emit_telemetry --intervalo 2      # uno cada 2 s (en vivo)
    python -m src.seed.emit_telemetry --lotes 10
    # o, mejor, desde el host:
    ./lab.sh streamlab emit
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import RAW_PATH, TEMP_ALERTA

# Semilla fija: el laboratorio tiene que dar lo mismo en todas las máquinas.
SEMILLA = 42

# ============================================================
# Parámetros de la flota
# ============================================================

NUM_ROBOTS = 40
ALMACENES = ["Rotterdam", "Valencia", "Hamburgo", "Lyon"]
SENSORES = ["temperatura", "bateria", "vibracion"]

# Ventana simulada: cada lote cubre un minuto de jornada.
MINUTOS_POR_LOTE = 1
LOTES_POR_DEFECTO = 30

# --- Ratios de suciedad ---
# Rotterdam es el almacén con mala cobertura: de ahí salió el incendio.
ALMACEN_LENTO = "Rotterdam"
RETRASO_BASE_LOTES = 1         # incluso conectado, sus lecturas llegan 1 lote tarde
RATIO_ROBOT_INESTABLE = 0.35   # 35% de los de Rotterdam pierden cobertura a ratos
CORTES_POR_ROBOT = (1, 2)      # cuántas veces se les cae la conexión
DURACION_CORTE = (3, 6)        # minutos que dura cada corte
RATIO_RELOJ_DESVIADO = 0.10    # 10% de robots con el reloj desajustado
DERIVA_RELOJ_SEG = 90          # hasta ±90 s de desfase
RATIO_DUPLICADO = 0.04         # 4% de lecturas reenviadas por reintento
RATIO_SENSOR_MUDO = 0.15       # 15% de robots se callan y ya no vuelven
RATIO_LECTURA_ABSURDA = 0.005  # 0.5% de temperaturas a 1000 °C

# Robots que de verdad se sobrecalientan: dan respuesta real a la demo.
NUM_ROBOTS_EN_RIESGO = 5


# ============================================================
# Modelo de la flota
# ============================================================

def construir_flota(rnd: random.Random, num_lotes: int) -> list[dict]:
    """Define los robots: id, almacén, y sus rarezas de reloj, red o avería."""
    en_riesgo = set(rnd.sample(range(NUM_ROBOTS), NUM_ROBOTS_EN_RIESGO))
    flota = []
    for i in range(NUM_ROBOTS):
        almacen = rnd.choice(ALMACENES)

        reloj = 0
        if rnd.random() < RATIO_RELOJ_DESVIADO:
            reloj = rnd.randint(-DERIVA_RELOJ_SEG, DERIVA_RELOJ_SEG)

        # Cortes de cobertura: solo en el almacén malo. Mientras dura el
        # corte el robot acumula, y al volver lo suelta todo de golpe.
        cortes: list[tuple[int, int]] = []
        if almacen == ALMACEN_LENTO and rnd.random() < RATIO_ROBOT_INESTABLE:
            for _ in range(rnd.randint(*CORTES_POR_ROBOT)):
                dur = rnd.randint(*DURACION_CORTE)
                ini = rnd.randint(0, max(0, num_lotes - dur - 1))
                cortes.append((ini, ini + dur))

        flota.append({
            "robot_id": f"RBT-{i:04d}",
            "almacen": almacen,
            "deriva_reloj_seg": reloj,
            "en_riesgo": i in en_riesgo,
            "cortes": cortes,
            # Los mudos se averían y ya no vuelven a emitir.
            "calla_en_lote": rnd.randint(8, 24) if rnd.random() < RATIO_SENSOR_MUDO else None,
        })
    return flota


def lote_de_llegada(robot: dict, minuto: int, num_lotes: int) -> int | None:
    """En qué lote entra una lectura medida en `minuto`.

    None significa que llegó después de cerrar la ventana de observación:
    esa lectura no se escribe. Es más honesto que amontonarla en el último
    lote, que crearía un pico que no existe en la realidad.
    """
    llegada = minuto
    if robot["almacen"] == ALMACEN_LENTO:
        llegada += RETRASO_BASE_LOTES
        # Si el minuto cae dentro de un corte, la lectura espera a que
        # vuelva la cobertura y sale con todas las demás acumuladas.
        for ini, fin in robot["cortes"]:
            if ini <= minuto < fin:
                llegada = max(llegada, fin)
                break
    return llegada if llegada < num_lotes else None


def valor_sensor(sensor: str, robot: dict, minuto: int, total_min: int, rnd: random.Random) -> float:
    """Valor plausible para un sensor. Los robots en riesgo se van calentando."""
    if sensor == "temperatura":
        base = 55 + rnd.gauss(0, 3)
        if robot["en_riesgo"]:
            # Sube progresivamente hasta pasar el umbral en la última parte.
            base += 30 * (minuto / max(total_min, 1))
        return round(base, 2)
    if sensor == "bateria":
        return round(max(5.0, 100 - 70 * (minuto / max(total_min, 1)) + rnd.gauss(0, 2)), 2)
    return round(abs(rnd.gauss(0.4, 0.15)), 3)  # vibracion


# ============================================================
# Generación de lecturas
# ============================================================

def generar_lecturas(flota: list[dict], num_lotes: int, inicio: datetime,
                     rnd: random.Random) -> tuple[dict[int, list[dict]], dict]:
    """Reparte las lecturas por lote de llegada, aplicando la suciedad.

    Devuelve (lecturas_por_lote, recuento_de_problemas). El recuento es el
    ground truth: cuántas lecturas hay de cada tipo de problema.
    """
    por_lote: dict[int, list[dict]] = {i: [] for i in range(num_lotes)}
    cuentas = {
        "total": 0, "retrasadas": 0, "muy_retrasadas": 0, "reloj_desviado": 0,
        "duplicadas": 0, "mudas_omitidas": 0, "fuera_de_ventana": 0,
        "absurdas": 0, "en_riesgo_real": 0,
    }
    total_min = num_lotes * MINUTOS_POR_LOTE

    for minuto in range(total_min):
        lote_natural = minuto // MINUTOS_POR_LOTE
        for robot in flota:
            # Un robot averiado deja de emitir y ya no vuelve.
            if robot["calla_en_lote"] is not None and lote_natural >= robot["calla_en_lote"]:
                cuentas["mudas_omitidas"] += len(SENSORES)
                continue

            ts_real = inicio + timedelta(minutes=minuto)
            # El reloj del robot puede ir desajustado: el ts que reporta miente.
            ts_evento = ts_real + timedelta(seconds=robot["deriva_reloj_seg"])
            if robot["deriva_reloj_seg"]:
                cuentas["reloj_desviado"] += len(SENSORES)

            lote_llegada = lote_de_llegada(robot, minuto, num_lotes)
            if lote_llegada is None:
                # Llegó cuando ya habíamos dejado de mirar.
                cuentas["fuera_de_ventana"] += len(SENSORES)
                continue
            retraso = lote_llegada - lote_natural
            if retraso > 0:
                cuentas["retrasadas"] += len(SENSORES)
                if retraso >= 3:
                    cuentas["muy_retrasadas"] += len(SENSORES)

            for sensor in SENSORES:
                valor = valor_sensor(sensor, robot, minuto, total_min, rnd)

                # Sensor descalibrado: temperatura imposible.
                absurda = sensor == "temperatura" and rnd.random() < RATIO_LECTURA_ABSURDA
                if absurda:
                    valor = 1000.0
                    cuentas["absurdas"] += 1
                elif sensor == "temperatura" and valor >= TEMP_ALERTA:
                    cuentas["en_riesgo_real"] += 1

                lectura = {
                    "robot_id": robot["robot_id"],
                    "almacen": robot["almacen"],
                    "sensor": sensor,
                    "valor": valor,
                    "ts_evento": ts_evento.isoformat().replace("+00:00", "Z"),
                    "intento": 1,
                }
                por_lote[lote_llegada].append(lectura)
                cuentas["total"] += 1

                # Reintento: la misma lectura vuelve a mandarse, a veces en
                # un lote posterior. Es el duplicado que hay que deduplicar.
                if rnd.random() < RATIO_DUPLICADO:
                    destino = lote_llegada + rnd.randint(0, 2)
                    if destino < num_lotes:
                        copia = dict(lectura)
                        copia["intento"] = 2
                        por_lote[destino].append(copia)
                        cuentas["duplicadas"] += 1
                        cuentas["total"] += 1

    # Dentro de cada lote, la red no respeta el orden de medición.
    for lote in por_lote.values():
        rnd.shuffle(lote)

    return por_lote, cuentas


# ============================================================
# Escritura
# ============================================================

def escribir_lote(destino: Path, indice: int, lecturas: list[dict]) -> Path:
    """Escribe un micro-lote como JSON Lines."""
    ruta = destino / f"lote-{indice:04d}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        for lectura in lecturas:
            f.write(json.dumps(lectura, ensure_ascii=False) + "\n")
    return ruta


def emitir(num_lotes: int = LOTES_POR_DEFECTO, intervalo: float = 0.0,
           limpiar: bool = True) -> dict:
    """Genera y escribe la emisión completa. Devuelve el manifiesto.

    Args:
        num_lotes: cuántos micro-lotes (cada uno = 1 minuto de jornada).
        intervalo: segundos reales entre lotes. 0 = todo de golpe.
        limpiar: vaciar `raw/` antes (una emisión nueva, no acumular).
    """
    rnd = random.Random(SEMILLA)
    destino = Path(RAW_PATH)

    if limpiar and destino.exists():
        for hijo in destino.iterdir():
            if hijo.name == ".gitkeep":
                continue
            shutil.rmtree(hijo) if hijo.is_dir() else hijo.unlink()
    destino.mkdir(parents=True, exist_ok=True)

    # Jornada simulada que termina "ahora", para que los tiempos tengan
    # sentido al mirarlos en la web.
    ahora = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    inicio = ahora - timedelta(minutes=num_lotes * MINUTOS_POR_LOTE)

    flota = construir_flota(rnd, num_lotes)
    por_lote, cuentas = generar_lecturas(flota, num_lotes, inicio, rnd)

    print(f"Emitiendo {num_lotes} lotes → {destino}")
    if intervalo:
        print(f"  ritmo: un lote cada {intervalo}s (en vivo)")

    for i in range(num_lotes):
        ruta = escribir_lote(destino, i, por_lote[i])
        print(f"  lote {i:>3}: {len(por_lote[i]):>4} lecturas → {ruta.name}")
        if intervalo and i < num_lotes - 1:
            time.sleep(intervalo)

    manifiesto = {
        "generado": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "semilla": SEMILLA,
        "lotes": num_lotes,
        "minutos_simulados": num_lotes * MINUTOS_POR_LOTE,
        "ventana": {
            "inicio": inicio.isoformat().replace("+00:00", "Z"),
            "fin": ahora.isoformat().replace("+00:00", "Z"),
        },
        "robots": NUM_ROBOTS,
        "almacenes": ALMACENES,
        "sensores": SENSORES,
        "umbral_alerta_c": TEMP_ALERTA,
        # Ground truth: con esto el alumno valida su detector.
        "ground_truth": cuentas,
    }
    (destino / "_emision.json").write_text(
        json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print()
    print(f"  lecturas escritas  : {cuentas['total']}")
    print(f"  llegan tarde       : {cuentas['retrasadas']}  (almacén {ALMACEN_LENTO})")
    print(f"    de ellas, +3 lotes: {cuentas['muy_retrasadas']}  (cortes de cobertura)")
    print(f"  duplicadas         : {cuentas['duplicadas']}  (reintentos)")
    print(f"  reloj desviado     : {cuentas['reloj_desviado']}")
    print(f"  nunca llegaron     : {cuentas['mudas_omitidas']} (robots averiados)"
          f" + {cuentas['fuera_de_ventana']} (fuera de ventana)")
    print(f"  absurdas (1000C)   : {cuentas['absurdas']}")
    print(f"  sobre {TEMP_ALERTA}C        : {cuentas['en_riesgo_real']}")
    print(f"\nManifiesto → {destino / '_emision.json'}")
    return manifiesto


def main() -> None:
    parser = argparse.ArgumentParser(description="Emisor de telemetría de la flota")
    parser.add_argument("--lotes", type=int, default=LOTES_POR_DEFECTO,
                        help=f"número de micro-lotes (default {LOTES_POR_DEFECTO})")
    parser.add_argument("--intervalo", type=float, default=0.0,
                        help="segundos reales entre lotes (0 = todo de golpe)")
    parser.add_argument("--conservar", action="store_true",
                        help="no vaciar raw/ antes de emitir")
    args = parser.parse_args()
    emitir(num_lotes=args.lotes, intervalo=args.intervalo, limpiar=not args.conservar)


if __name__ == "__main__":
    main()
