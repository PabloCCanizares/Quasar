"""Cargador lazy de las tablas como pandas DataFrames.

Las 4 tablas (robots, sensors_readings, events, maintenances) caben de sobra
en memoria (~17 MB total). Las cargamos UNA vez por proceso y las cacheamos.

Fuente de datos, por orden de preferencia:
  1. Capa **silver** (parquet) escrita por el ETL Spark (`src.spark.run_pipeline`).
     Columnar → se lee mucho más rápido que re-parseando JSON en cada arranque.
  2. Capa **raw** (JSON Lines) del seed, como fallback si el ETL no se ha corrido.

La suciedad del Tema 5 se preserva idéntica en ambas capas (el ETL ingesta,
no limpia), así que los bloques de preprocesamiento funcionan igual lean de
donde lean. Si se regenera el seed o el silver, reinicia el contenedor
(`./lab.sh preprolab restart`) para invalidar el cache.

Por qué pandas y no Spark en los endpoints:
- Datasets pequeños → pandas es ~100x más rápido que el arranque de Spark.
- Mejor integración con Plotly (JSON directo desde dataframes).
- Spark hace el trabajo pesado en la capa silver; aquí solo se lee.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from src.config import RAW_PATH, SILVER_PATH

# Las tablas que el dataset genera. El orden importa para la UI.
TABLES: list[str] = ["robots", "sensors_readings", "events", "maintenances"]

# Cache en memoria del proceso.
_cache: Dict[str, pd.DataFrame] = {}


def _read_silver(name: str) -> Optional[pd.DataFrame]:
    """Lee la tabla desde la capa silver (parquet) si el ETL ya la generó."""
    silver_dir: Path = SILVER_PATH / name
    if silver_dir.is_dir() and any(silver_dir.glob("*.parquet")):
        return pd.read_parquet(silver_dir)
    return None


def _read_raw(name: str) -> pd.DataFrame:
    """Lee la tabla desde la capa raw (JSON Lines). Fallback si no hay silver."""
    path: Path = RAW_PATH / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encuentra {path}. Ejecuta `./lab.sh preprolab seed` para generar los datos."
        )
    return pd.read_json(path, lines=True)


def load_table(name: str) -> pd.DataFrame:
    """Carga una tabla (silver parquet o raw JSON) y la cachea.

    Args:
        name: nombre de la tabla (robots, sensors_readings, events, maintenances).
    """
    if name not in TABLES:
        raise ValueError(f"Tabla desconocida: {name}. Válidas: {TABLES}")

    if name in _cache:
        return _cache[name]

    df = _read_silver(name)
    if df is None:
        df = _read_raw(name)
    _cache[name] = df
    return df


def load_all() -> Dict[str, pd.DataFrame]:
    """Carga las 4 tablas (con caché). Útil para el endpoint overview."""
    return {name: load_table(name) for name in TABLES}


def clear_cache() -> None:
    """Invalida el cache. Útil para tests."""
    _cache.clear()


def is_seeded() -> bool:
    """True si las 4 tablas existen en disco (en silver parquet o raw JSON)."""
    return all(
        (SILVER_PATH / name).is_dir() or (RAW_PATH / f"{name}.json").exists()
        for name in TABLES
    )
