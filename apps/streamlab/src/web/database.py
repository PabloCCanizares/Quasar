"""StreamLab — wrapper sobre `infra.shared.mongo`.

StreamLab no usa Neo4j: su material son series temporales, no relaciones.
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
from src.config import MONGO_DB


def get_db():
    """Base de datos async de StreamLab (motor)."""
    return get_async_db(MONGO_DB)


def get_sync_db():
    """Base de datos síncrona de StreamLab (pymongo)."""
    return _shared_sync_db(MONGO_DB)


__all__ = [
    "get_async_client",
    "get_sync_client",
    "get_db",
    "get_sync_db",
]
