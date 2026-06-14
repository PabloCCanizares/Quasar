"""Estado agregado del ecosistema.

Consulta health + lab/status de las 3 apps (server-side con httpx, así
funciona aunque una app esté caída y no hay CORS). Devuelve una vista
unificada para el dashboard del Hub.
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter

from src.config import APPS

router = APIRouter(prefix="/api/hub", tags=["hub"])


async def _probe_app(key: str, meta: dict) -> dict:
    """Consulta health + status de una app. Tolera que esté caída."""
    base = meta["url_internal"]
    result = {
        "key": key,
        "name": meta["name"],
        "tagline": meta["tagline"],
        "description": meta["description"],
        "url_public": meta["url_public"],
        "color": meta["color"],
        "online": False,
        "blocks": {},
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            health = await client.get(f"{base}/api/health")
            result["online"] = health.status_code == 200
            if result["online"]:
                status = await client.get(f"{base}{meta['status_path']}")
                if status.status_code == 200:
                    data = status.json()
                    result["blocks"] = data.get("blocks", {})
                    # SocialLab anida neo4j/ml en lugar de un dict plano
                    if "neo4j" in data or "ml" in data:
                        merged = {}
                        merged.update({f"neo4j:{k}": v for k, v in data.get("neo4j", {}).items()})
                        merged.update({f"ml:{k}": v for k, v in data.get("ml", {}).items()})
                        result["blocks"] = merged
    except Exception:
        result["online"] = False
    return result


@router.get("/status")
async def ecosystem_status() -> dict:
    """Estado agregado de las 3 apps en una sola respuesta."""
    probes = await asyncio.gather(*[_probe_app(k, m) for k, m in APPS.items()])
    total_blocks = sum(len(p["blocks"]) for p in probes)
    unlocked = sum(sum(1 for v in p["blocks"].values() if v) for p in probes)
    return {
        "apps": probes,
        "summary": {
            "apps_online": sum(1 for p in probes if p["online"]),
            "apps_total": len(probes),
            "blocks_unlocked": unlocked,
            "blocks_total": total_blocks,
        },
    }
