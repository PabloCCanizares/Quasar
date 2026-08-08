"""LLM Lab — wrapper sobre infra.shared.mongo y infra.shared.neo4j."""

from __future__ import annotations

from infra.shared.mongo import (
    get_async_client,
    get_async_db,
    get_sync_client,
)
from infra.shared.mongo import (
    get_sync_db as _shared_sync_db,
)
from infra.shared.neo4j import neo4j_write  # noqa: F401
from src.config import MONGO_DB


def get_db():
    return get_async_db(MONGO_DB)


def get_sync_db():
    return _shared_sync_db(MONGO_DB)


__all__ = [
    "get_async_client",
    "get_sync_client",
    "get_db",
    "get_sync_db",
    "neo4j_write",
]
