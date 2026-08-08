"""
Generador del dataset sintético de la flota de robots para PreproLab.

Construye 4 tablas relacionadas que simulan los registros operativos de una
empresa logística europea con miles de robots autónomos en varios almacenes.
Cada tabla viene con problemas INTENCIONADOS que el alumno debe identificar
y resolver en los bloques del Tema 5.

Tablas generadas (en infra/data/preprolab/raw/, JSON Lines):
  - robots.json            catálogo con metadatos + variable objetivo
  - sensors_readings.json  telemetría temporal (últimos 60 días)
  - events.json            alertas/incidentes etiquetados por operarios
  - maintenances.json      historial de mantenimientos correctivos y preventivos

Variable objetivo:
  robots.failure_next_48h  (1 = el robot falla en próximas 48h, 0 = no)

Problemas inyectados (mapeados al Tema 5):
  1. MCAR — sensor que falla aleatoriamente (valor null al azar)
  2. MAR  — firmware viejo no reporta battery_health_v2 (depende del firmware OBSERVADO)
  3. MNAR — "Manufactura Centauri" no comparte consumo_kw (depende del valor OCULTO)
  4. Outliers de medición: temperaturas de 1000°C por sensor descalibrado
  5. Outliers extremos válidos: robots de prueba a velocidad/temperatura máxima
  6. Outliers fuera de rango: fechas en el futuro, duraciones negativas
  7. Class noise — ~5% eventos mal etiquetados por operarios
  8. Duplicados — ~3% robots registrados dos veces tras fusión de almacenes
  9. Fechas en 5 formatos distintos (epoch, ISO, US, EU, relativo)
  10. Encoding roto — nombres europeos con mojibake (Müller → MÃ¼ller)
  11. Multivaluadas — sensores_activos como lista codificada en string CSV
  12. Redundancia — batería_pct, voltaje_v y consumo_total_kwh altamente correlacionados
  13. PII plantada — emails y teléfonos falsos en descripciones de eventos (~5%)
  14. Descripciones extremas — eventos con texto vacío o con >5000 caracteres

Uso:
    docker compose exec app-preprolab python -m src.seed.generate_robot_fleet
    # o, mejor, desde el host:
    ./lab.sh preprolab seed
"""

from __future__ import annotations

import json
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import RAW_PATH

# Semilla fija para reproducibilidad.
random.seed(42)

# ============================================================
# Parámetros del generador
# ============================================================

NUM_ROBOTS = 2000
NUM_READINGS_PER_ROBOT_AVG = 50      # → ~100k readings
NUM_EVENTS_PER_ROBOT_AVG = 5         # → ~10k events
NUM_MAINTENANCES_PER_ROBOT_AVG = 2   # → ~4k mantenimientos

# Ratios de inyección de problemas
MCAR_VALUE_RATIO = 0.03               # 3% readings con valor null aleatorio
MAR_FIRMWARE_VIEJO_RATIO = 0.30       # 30% de robots con firmware < 2.0
MNAR_FABRICANTE_OCULTO = "Manufactura Centauri"   # no reporta consumo_kw
OUTLIER_MEDICION_RATIO = 0.005        # 0.5% temperaturas absurdas
OUTLIER_EXTREMO_VALIDO_RATIO = 0.002  # 0.2% robots de prueba en extremos válidos
OUTLIER_FUERA_RANGO_RATIO = 0.002     # 0.2% fechas futuras/duraciones negativas
CLASS_NOISE_RATIO = 0.05              # 5% eventos mal etiquetados
DUPLICATE_ROBOT_RATIO = 0.03          # 3% robots duplicados
ENCODING_BROKEN_RATIO = 0.05          # 5% nombres con mojibake
PII_PLANTED_RATIO = 0.05              # 5% descripciones con email/teléfono
DESC_EXTREMA_RATIO = 0.03             # 3% descripciones vacías o larguísimas

# ============================================================
# Vocabularios
# ============================================================

FABRICANTES = [
    "Manufactura Orion",
    "Manufactura Sirius",
    "Manufactura Centauri",   # el que oculta consumo_kw (MNAR)
    "Manufactura Vega",
]

MODELOS = ["RX-100", "RX-200", "RX-300", "Jumper-50", "Jumper-100", "Atlas-V"]

ALMACENES = [
    "Madrid-Sur", "Barcelona-Norte", "Sevilla-Este", "Bilbao-Oeste",
    "Valencia-Centro", "Zaragoza-Este", "Málaga-Sur", "Lisboa-Norte",
    "París-Sur", "Roma-Norte", "Berlín-Centro", "Múnich-Sur",
]

ZONAS_ALMACEN = ["picking", "almacenamiento", "carga", "expedición"]

TIPOS_SENSOR = [
    "lidar_2d", "lidar_3d", "imu", "camera_rgb", "camera_depth",
    "battery", "temp_motor", "temp_cpu", "encoder_wheel",
]

TIPOS_EVENTO = [
    "sensor_fallo",
    "colision_evitada",
    "perdida_localizacion",
    "bateria_baja",
    "obstaculo_dinamico",
    "mantenimiento_programado",
    "falso_positivo",
    "comunicacion_perdida",
    "actualizacion_firmware_fallida",
]

SEVERIDADES = ["INFO", "WARN", "ERROR", "CRITICAL"]   # ordinal (1 → 4)

TIPOS_MANTENIMIENTO = [
    "preventivo", "correctivo", "inspeccion", "actualizacion_firmware",
]

FIRMWARE_VERSIONS = ["1.0", "1.5", "2.0", "2.3", "2.5"]

# Nombres con caracteres no-ASCII para ejercitar el bloque de encoding.
NOMBRES_TECNICOS = [
    "Müller", "García", "Schneider", "Martínez", "Schmidt", "Rossi",
    "Lefèvre", "Žužul", "Henriques", "Søren", "Üzümcü", "Carvalho",
    "Núñez", "Borgström", "Cañizares", "Pérez", "Çelik", "Møller",
]

# ============================================================
# Helpers
# ============================================================


def _random_date(start: datetime, end: datetime) -> datetime:
    """Fecha aleatoria entre dos timestamps."""
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def _format_date_in_random_format(dt: datetime) -> str:
    """Devuelve la fecha en uno de 5 formatos (epoch / ISO / US / EU / relativo).

    Esto es lo que el alumno debe normalizar en el bloque `transform`.
    """
    fmt = random.choice(["epoch", "iso", "us", "eu", "relativo"])
    if fmt == "epoch":
        return str(int(dt.timestamp()))
    if fmt == "iso":
        return dt.isoformat()
    if fmt == "us":
        return dt.strftime("%m/%d/%Y %I:%M %p")
    if fmt == "eu":
        return dt.strftime("%d-%m-%Y %H:%M")
    # relativo
    diff = datetime.now(timezone.utc) - dt
    if diff.days > 0:
        return f"hace {diff.days} días"
    horas = diff.seconds // 3600
    if horas > 0:
        return f"hace {horas} horas"
    minutos = diff.seconds // 60
    return f"hace {minutos} minutos"


def _break_encoding(text: str) -> str:
    """Simula mojibake al pasar UTF-8 → Latin-1 → UTF-8 mal."""
    replacements = {
        "ü": "Ã¼", "ñ": "Ã±", "á": "Ã¡", "é": "Ã©", "í": "Ã­",
        "ó": "Ã³", "ú": "Ãº", "ç": "Ã§", "Ü": "Ãœ", "Ñ": "Ã‘",
        "ø": "Ã¸", "Ž": "Å½", "ž": "Å¾",
    }
    out = text
    for original, broken in replacements.items():
        out = out.replace(original, broken)
    return out


def _maybe_break_encoding(text: str, prob: float = ENCODING_BROKEN_RATIO) -> str:
    if random.random() < prob:
        return _break_encoding(text)
    return text


def _fake_phone() -> str:
    return f"+34 6{random.randint(10_000_000, 99_999_999)}"


def _fake_email(name: str) -> str:
    handle = name.lower().replace("ü", "u").replace("ñ", "n").replace("á", "a")
    handle = "".join(c for c in handle if c.isalnum())
    return f"{handle}@logistics.example"


def _long_lorem(length: int = 5000) -> str:
    """Genera una descripción artificialmente larga."""
    word = "lorem ipsum dolor sit amet "
    return (word * (length // len(word) + 1))[:length]


# ============================================================
# Tabla 1: robots
# ============================================================


def generate_robots() -> list[dict]:
    """Genera la tabla maestra de robots con problemas inyectados.

    Inyecciones:
      - MAR (battery_health_v2 null si firmware < 2.0)
      - MNAR (consumo_kw null si Manufactura Centauri)
      - Outliers fuera de rango (fechas futuras)
      - Multivaluada (sensores_activos como CSV)
      - Redundancia (bateria_pct, voltaje_v, consumo_total_kwh correlacionados)
      - Duplicados (3% al final)
    """
    now = datetime.now(timezone.utc)
    robots: list[dict] = []

    for i in range(NUM_ROBOTS):
        robot_id = f"r_{i:05d}"

        fabricante = random.choice(FABRICANTES)
        modelo = random.choice(MODELOS)

        # Firmware: 30% son viejos (< 2.0). Eso luego define el MAR.
        if random.random() < MAR_FIRMWARE_VIEJO_RATIO:
            firmware = random.choice(["1.0", "1.5"])
        else:
            firmware = random.choice(["2.0", "2.3", "2.5"])

        fecha_alta = _random_date(
            now - timedelta(days=365 * 3),
            now - timedelta(days=30),
        )
        # Outliers fuera de rango: ~0.2% con fecha futura.
        if random.random() < OUTLIER_FUERA_RANGO_RATIO:
            fecha_alta = now + timedelta(days=random.randint(1, 365))

        almacen = random.choice(ALMACENES)
        zona = random.choice(ZONAS_ALMACEN)

        # Multivaluada: lista de sensores activos como CSV.
        sensores_activos = random.sample(TIPOS_SENSOR, k=random.randint(3, 7))
        sensores_activos_csv = ", ".join(sensores_activos)

        # MAR: battery_health_v2 solo se reporta con firmware >= 2.0.
        if firmware >= "2.0":
            battery_health_v2 = round(random.uniform(0.4, 1.0), 3)
        else:
            battery_health_v2 = None

        # MNAR: Manufactura Centauri no reporta consumo_kw.
        if fabricante == MNAR_FABRICANTE_OCULTO:
            consumo_kw = None
        else:
            consumo_kw = round(random.uniform(0.5, 5.0), 2)

        # Redundancia: tres features altamente correlacionadas.
        bateria_pct = random.uniform(20, 100)
        voltaje_v = bateria_pct * 0.4 + random.uniform(-1, 1)
        consumo_total_kwh = bateria_pct * 0.08 + random.uniform(-0.3, 0.3)

        # Outliers extremos válidos: ~0.2% con valores en el límite alto.
        if random.random() < OUTLIER_EXTREMO_VALIDO_RATIO:
            bateria_pct = 100.0
            voltaje_v = 60.0
            consumo_total_kwh = 12.0

        # ----------------------------------------------------------
        # Variable objetivo: failure_next_48h
        # Probabilidad de fallo en próximas 48h basada en señales reales.
        # ----------------------------------------------------------
        prob_fallo = 0.08  # baseline
        if bateria_pct < 30:
            prob_fallo += 0.30
        if firmware == "1.0":
            prob_fallo += 0.20
        if firmware == "1.5":
            prob_fallo += 0.10
        if battery_health_v2 is not None and battery_health_v2 < 0.6:
            prob_fallo += 0.20
        # Robots viejos (alta antigüedad) tienen más fallos.
        antiguedad_dias = (now - fecha_alta).days
        if antiguedad_dias > 365 * 2:
            prob_fallo += 0.10
        prob_fallo = min(0.95, prob_fallo)
        failure_next_48h = 1 if random.random() < prob_fallo else 0

        robots.append({
            "id": robot_id,
            "modelo": modelo,
            "fabricante": fabricante,
            "fecha_alta": _format_date_in_random_format(fecha_alta),
            "almacen": _maybe_break_encoding(almacen),
            "zona": zona,
            "firmware_version": firmware,
            "sensores_activos": sensores_activos_csv,
            "battery_health_v2": battery_health_v2,
            "consumo_kw": consumo_kw,
            "bateria_pct": round(bateria_pct, 1),
            "voltaje_v": round(voltaje_v, 2),
            "consumo_total_kwh": round(consumo_total_kwh, 2),
            "failure_next_48h": failure_next_48h,
        })

    # ----------------------------------------------------------
    # Duplicados (3%): mismo robot, distinto id, datos casi iguales
    # pero con encoding roto en algún campo para que sea detectable.
    # ----------------------------------------------------------
    num_duplicates = int(NUM_ROBOTS * DUPLICATE_ROBOT_RATIO)
    for k in range(num_duplicates):
        original = random.choice(robots[:NUM_ROBOTS])
        dup = dict(original)
        dup["id"] = f"r_{NUM_ROBOTS + k:05d}"
        # Rompemos encoding del almacén para que el dedup por exact match falle
        # pero un análisis de correlación / fuzzy match sí los detecte.
        dup["almacen"] = _break_encoding(dup["almacen"])
        robots.append(dup)

    return robots


# ============================================================
# Tabla 2: sensors_readings
# ============================================================


def generate_sensor_readings(robots: list[dict]) -> list[dict]:
    """Genera la telemetría temporal. Inyecciones: MCAR + outliers de medición."""
    now = datetime.now(timezone.utc)
    readings: list[dict] = []

    # Solo los robots "originales" (no duplicados) generan readings reales.
    for robot in robots[:NUM_ROBOTS]:
        n_readings = max(1, int(random.gauss(NUM_READINGS_PER_ROBOT_AVG, 12)))

        for _ in range(n_readings):
            timestamp = _random_date(now - timedelta(days=60), now)
            sensor_type = random.choice(TIPOS_SENSOR)

            # Valores base normales.
            valor = round(random.uniform(0, 100), 2)
            bateria = round(random.uniform(20, 100), 1)
            temperatura = round(random.uniform(20, 60), 1)

            # MCAR (~3%): valor null por sensor fallido aleatorio.
            if random.random() < MCAR_VALUE_RATIO:
                valor = None

            # Outliers de medición (~0.5%): temperatura absurda.
            if random.random() < OUTLIER_MEDICION_RATIO:
                temperatura = 1000.0

            # Outliers extremos válidos (~0.2%): robot de prueba.
            if random.random() < OUTLIER_EXTREMO_VALIDO_RATIO:
                valor = 99.99
                temperatura = 85.0  # alto pero válido

            readings.append({
                "robot_id": robot["id"],
                "timestamp": _format_date_in_random_format(timestamp),
                "sensor_type": sensor_type,
                "valor": valor,
                "bateria_pct": bateria,
                "temperatura": temperatura,
            })

    return readings


# ============================================================
# Tabla 3: events
# ============================================================


def generate_events(robots: list[dict]) -> list[dict]:
    """Eventos etiquetados por operarios. Inyecciones: class noise, encoding, PII, descripciones extremas."""
    now = datetime.now(timezone.utc)
    events: list[dict] = []

    for robot in robots[:NUM_ROBOTS]:
        n_events = max(0, int(random.gauss(NUM_EVENTS_PER_ROBOT_AVG, 3)))

        for _ in range(n_events):
            timestamp = _random_date(now - timedelta(days=90), now)
            tipo_real = random.choice(TIPOS_EVENTO)
            severidad_real = random.choice(SEVERIDADES)
            tecnico = random.choice(NOMBRES_TECNICOS)
            tecnico = _maybe_break_encoding(tecnico)

            # Class noise (~5%): operario se equivoca con tipo/severidad.
            if random.random() < CLASS_NOISE_RATIO:
                tipo_etiquetado = random.choice(TIPOS_EVENTO)
                severidad_etiquetada = random.choice(SEVERIDADES)
            else:
                tipo_etiquetado = tipo_real
                severidad_etiquetada = severidad_real

            descripcion = (
                f"Evento {tipo_etiquetado} en robot {robot['id']} "
                f"reportado por {tecnico}."
            )

            # PII plantada (~5%).
            if random.random() < PII_PLANTED_RATIO:
                descripcion += (
                    f" Contactar a {_fake_email(tecnico)} "
                    f"o al teléfono {_fake_phone()}."
                )

            # Descripciones extremas (~3%): vacías o larguísimas.
            if random.random() < DESC_EXTREMA_RATIO:
                if random.random() < 0.5:
                    descripcion = ""
                else:
                    descripcion = _long_lorem(5000)

            events.append({
                "robot_id": robot["id"],
                "timestamp": _format_date_in_random_format(timestamp),
                "tipo": tipo_etiquetado,
                "severidad": severidad_etiquetada,
                "descripcion": descripcion,
                "tecnico": tecnico,
            })

    return events


# ============================================================
# Tabla 4: maintenances
# ============================================================


def generate_maintenances(robots: list[dict]) -> list[dict]:
    """Historial de mantenimientos. Inyecciones: encoding, outliers fuera de rango."""
    now = datetime.now(timezone.utc)
    maintenances: list[dict] = []

    for robot in robots[:NUM_ROBOTS]:
        n_mant = max(0, int(random.gauss(NUM_MAINTENANCES_PER_ROBOT_AVG, 1)))

        for _ in range(n_mant):
            fecha = _random_date(now - timedelta(days=365), now)
            tipo = random.choice(TIPOS_MANTENIMIENTO)
            duracion = round(random.uniform(0.5, 8.0), 1)
            tecnico = _maybe_break_encoding(random.choice(NOMBRES_TECNICOS))
            coste = round(random.uniform(50, 2000), 2)

            # Outliers fuera de rango: ~0.2% duración negativa (error de registro).
            if random.random() < OUTLIER_FUERA_RANGO_RATIO:
                duracion = -1.0 * random.uniform(0.5, 5.0)

            maintenances.append({
                "robot_id": robot["id"],
                "fecha": _format_date_in_random_format(fecha),
                "tipo": tipo,
                "duracion_horas": duracion,
                "tecnico": tecnico,
                "coste_euros": coste,
            })

    return maintenances


# ============================================================
# Escritura
# ============================================================


def write_json_lines(data: list[dict], name: str) -> Path:
    """Escribe una lista de dicts como JSON Lines (.json con un objeto por línea).

    Es el formato que Spark lee por defecto con `spark.read.json(path)`.
    """
    path = RAW_PATH / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"  {name:20s} {len(data):>10,d} records → {path} ({size_mb:.1f} MB)")
    return path


def main() -> None:
    print("=" * 64)
    print("PreproLab — Generador del dataset de la flota de robots")
    print("=" * 64)
    print(f"Output: {RAW_PATH}")
    print("Semilla: 42 (reproducible)")
    print()

    print("[1/4] Generando tabla robots...")
    robots = generate_robots()
    write_json_lines(robots, "robots")

    print("[2/4] Generando tabla sensors_readings...")
    readings = generate_sensor_readings(robots)
    write_json_lines(readings, "sensors_readings")

    print("[3/4] Generando tabla events...")
    events = generate_events(robots)
    write_json_lines(events, "events")

    print("[4/4] Generando tabla maintenances...")
    maintenances = generate_maintenances(robots)
    write_json_lines(maintenances, "maintenances")

    # ----------------------------------------------------------
    # Resumen + verificaciones (sanity check)
    # ----------------------------------------------------------
    robots_originales = robots[:NUM_ROBOTS]
    pos = sum(r["failure_next_48h"] for r in robots_originales)
    neg = NUM_ROBOTS - pos
    duplicates = len(robots) - NUM_ROBOTS

    none_battery = sum(1 for r in robots_originales if r["battery_health_v2"] is None)
    none_consumo = sum(1 for r in robots_originales if r["consumo_kw"] is None)
    none_valor = sum(1 for r in readings if r["valor"] is None)
    outliers_temp = sum(1 for r in readings if r["temperatura"] == 1000.0)
    eventos_vacios = sum(1 for e in events if e["descripcion"] == "")

    print()
    print("=" * 64)
    print("Resumen")
    print("=" * 64)
    print(f"  robots:            {len(robots):>8,d}  (originales: {NUM_ROBOTS:,d} + duplicados: {duplicates:,d})")
    print(f"  sensors_readings:  {len(readings):>8,d}")
    print(f"  events:            {len(events):>8,d}")
    print(f"  maintenances:      {len(maintenances):>8,d}")
    print()
    print("Variable objetivo (failure_next_48h):")
    print(f"  positivos: {pos:>5,d}  ({100*pos/NUM_ROBOTS:.1f}%)")
    print(f"  negativos: {neg:>5,d}  ({100*neg/NUM_ROBOTS:.1f}%)")
    print()
    print("Verificación de problemas inyectados:")
    print(f"  MAR (battery_health_v2 null por firmware viejo): {none_battery:>6,d} robots")
    print(f"  MNAR (consumo_kw null por fabricante oculto):    {none_consumo:>6,d} robots")
    print(f"  MCAR (valor null en readings):                   {none_valor:>6,d} readings")
    print(f"  Outliers de medición (temp=1000°C):              {outliers_temp:>6,d} readings")
    print(f"  Eventos con descripción vacía:                   {eventos_vacios:>6,d} events")


if __name__ == "__main__":
    main()
