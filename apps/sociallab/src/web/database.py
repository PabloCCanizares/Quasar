"""SocialLab — wrapper sobre `infra.shared.mongo` y `infra.shared.neo4j`.

Inyecta el nombre de la BD de SocialLab para que el resto del código de la app
pueda llamar a `get_db()` sin tener que pasar el nombre de la BD cada vez.

La web usa `get_async_client()` / `get_db()`. Los scripts de seed/spark usan
`get_sync_client()` / `get_sync_db()`.
"""

from __future__ import annotations

from infra.shared.mongo import (
    get_async_client,
    get_async_db,
    get_sync_client,
)
from infra.shared.mongo import (
    get_sync_db as _shared_sync_db,
)
from infra.shared.neo4j import neo4j_write  # noqa: F401 (re-export)
from src.config import MONGO_DB


def get_db():
    """Base de datos async de SocialLab (motor)."""
    return get_async_db(MONGO_DB)


def get_sync_db():
    """Base de datos síncrona de SocialLab (pymongo)."""
    return _shared_sync_db(MONGO_DB)


__all__ = [
    "get_async_client",
    "get_sync_client",
    "get_db",
    "get_sync_db",
    "neo4j_write",
]
