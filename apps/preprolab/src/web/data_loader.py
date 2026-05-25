"""Cargador lazy de las tablas raw como pandas DataFrames.

Las 4 tablas (robots, sensors_readings, events, maintenances) caben de sobra
en memoria (~17 MB total). Las cargamos UNA vez por proceso y las cacheamos.

Si el seed se regenera mientras la app corre, basta con reiniciar el
contenedor (`./lab.sh preprolab restart`) para invalidar el cache.

Por qué pandas y no Spark para EDA:
- Datasets pequeños → pandas es ~100x más rápido que Spark startup.
- Mejor integración con Plotly (JSON directo desde dataframes).
- Spark queda reservado para los bloques heavyweight (silver/gold ETL).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from src.config import RAW_PATH

# Las tablas que el dataset genera. El orden importa para la UI.
TABLES: list[str] = ["robots", "sensors_readings", "events", "maintenances"]

# Cache en memoria del proceso.
_cache: Dict[str, pd.DataFrame] = {}


def load_table(name: str) -> pd.DataFrame:
    """Carga una tabla JSON Lines y la cachea. Lanza FileNotFoundError si no existe.

    Args:
        name: nombre de la tabla (robots, sensors_readings, events, maintenances).
    """
    if name not in TABLES:
        raise ValueError(f"Tabla desconocida: {name}. Válidas: {TABLES}")

    if name in _cache:
        return _cache[name]

    path: Path = RAW_PATH / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encuentra {path}. Ejecuta `./lab.sh preprolab seed` para generar los datos."
        )

    # JSON Lines: un objeto por línea.
    df = pd.read_json(path, lines=True)
    _cache[name] = df
    return df


def load_all() -> Dict[str, pd.DataFrame]:
    """Carga las 4 tablas (con caché). Útil para el endpoint overview."""
    return {name: load_table(name) for name in TABLES}


def clear_cache() -> None:
    """Invalida el cache. Útil para tests."""
    _cache.clear()


def is_seeded() -> bool:
    """True si las 4 tablas existen en disco."""
    return all((RAW_PATH / f"{name}.json").exists() for name in TABLES)
