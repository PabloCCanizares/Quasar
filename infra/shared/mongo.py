"""Clientes MongoDB compartidos.

La web (FastAPI) usa el cliente async (motor). Los scripts de seed/spark usan
el cliente síncrono (pymongo).

Las apps llaman a `get_async_db(db_name)` o `get_sync_db(db_name)` pasando el
nombre de su base de datos (p.ej. `"sociallab"`, `"preprolab"`).
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from infra.shared.config_base import MONGO_URI

# --- Async (cacheado por proceso) ---
_async_client: AsyncIOMotorClient | None = None


def get_async_client() -> AsyncIOMotorClient:
    """Cliente async cacheado a nivel de proceso. Reutilizable entre requests."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(MONGO_URI)
    return _async_client


def get_async_db(db_name: str):
    """Devuelve la base de datos async para la app indicada."""
    return get_async_client()[db_name]


# --- Sync (un cliente por llamada, para scripts) ---
def get_sync_client() -> MongoClient:
    return MongoClient(MONGO_URI)


def get_sync_db(db_name: str):
    """Devuelve la base de datos síncrona para la app indicada."""
    return get_sync_client()[db_name]
