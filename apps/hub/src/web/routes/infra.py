"""Salud de la infraestructura + estado de los datos.

Sonda la columna vertebral del ecosistema (MongoDB, Neo4j) y comprueba si
cada app tiene datos generados. Es lo que distingue a un panel de control
de datos de un simple índice de apps.

Sondeos ligeros (sin drivers pesados):
  - Mongo / Neo4j: conexión TCP al puerto → reachable.
  - Datos: existencia de los archivos clave en el data lake montado (ro)
    + conteo de documentos en Mongo (pymongo, opcional).
"""

from __future__ import annotations

import socket
from pathlib import Path

from fastapi import APIRouter

from src.config import (
    APPS, DATA_ROOT,
    MONGO_HOST, MONGO_PORT, NEO4J_HOST, NEO4J_BOLT_PORT, NEO4J_HTTP_PORT,
)

router = APIRouter(prefix="/api/hub", tags=["hub-infra"])


def _tcp_reachable(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _mongo_counts() -> dict:
    """Conteos por BD de las apps (best-effort con pymongo)."""
    try:
        from pymongo import MongoClient
        client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}", serverSelectionTimeoutMS=1500)
        client.admin.command("ping")
        out = {}
        for db_name in ("sociallab", "preprolab", "llmprep"):
            db = client[db_name]
            collections = db.list_collection_names()
            counts = {}
            for c in collections[:8]:
                try:
                    counts[c] = db[c].estimated_document_count()
                except Exception:
                    pass
            out[db_name] = counts
        client.close()
        return out
    except Exception:
        return {}


# Archivos clave que indican "datos generados" por app.
_DATA_MARKERS = {
    "sociallab": ("sociallab/raw/users.json", "Datos sucios generados"),
    "preprolab": ("preprolab/raw/robots.json", "Flota de robots generada"),
    "llmprep": ("llmprep/raw/corpus.json", "Corpus generado"),
}


def _data_state() -> dict:
    """Por app: si el seed se ha generado (archivo) y tamaño."""
    root = Path(DATA_ROOT)
    mongo = _mongo_counts()
    out = {}
    for app_key, (rel, label) in _DATA_MARKERS.items():
        f = root / rel
        seeded = f.exists() and f.stat().st_size > 0
        size_mb = round(f.stat().st_size / 1024 / 1024, 1) if seeded else 0
        db_counts = mongo.get(app_key, {})
        loaded = sum(db_counts.values()) > 0 if db_counts else False
        out[app_key] = {
            "seeded": seeded,
            "seed_label": label,
            "seed_size_mb": size_mb,
            "db_loaded": loaded,
            "db_counts": db_counts,
        }
    return out


@router.get("/infra")
async def infra_status() -> dict:
    """Salud de la infra + estado de datos por app."""
    mongo_up = _tcp_reachable(MONGO_HOST, MONGO_PORT)
    neo4j_bolt = _tcp_reachable(NEO4J_HOST, NEO4J_BOLT_PORT)
    neo4j_http = _tcp_reachable(NEO4J_HOST, NEO4J_HTTP_PORT)
    return {
        "infra": {
            "mongodb": {"name": "MongoDB", "port": MONGO_PORT, "online": mongo_up,
                        "role": "Base documental — usuarios, posts, métricas"},
            "neo4j": {"name": "Neo4j", "port": NEO4J_BOLT_PORT, "online": neo4j_bolt and neo4j_http,
                      "browser": "http://localhost:7474",
                      "role": "Grafo — follows, comunidades, SIMILAR_TO"},
        },
        "data": _data_state(),
    }
