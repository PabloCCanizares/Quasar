"""
Conexión a MongoDB — síncrona (pymongo) y asíncrona (motor).
La web usa motor. Los scripts de seed/spark usan pymongo.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from src.config import MONGO_URI, MONGO_DB

# --- Async (para FastAPI) ---
_async_client: AsyncIOMotorClient | None = None


def get_async_client() -> AsyncIOMotorClient:
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(MONGO_URI)
    return _async_client


def get_db():
    return get_async_client()[MONGO_DB]


# --- Sync (para scripts, seed, spark) ---
def get_sync_client() -> MongoClient:
    return MongoClient(MONGO_URI)


def get_sync_db():
    return get_sync_client()[MONGO_DB]


# --- Neo4j (sync, best-effort para sincronización live) ---
def neo4j_write(cypher: str, params: dict | None = None):
    """Ejecuta una escritura en Neo4j. Falla silenciosamente si Neo4j no está disponible."""
    try:
        from neo4j import GraphDatabase
        from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run(cypher, params or {})
        driver.close()
    except Exception:
        pass  # Neo4j is optional — live sync is best-effort
