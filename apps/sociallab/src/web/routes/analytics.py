"""Agregador de los routers de analytics.

Para cada bloque de Cypher (basic, intermediate, advanced) decide en tiempo
de import si usa la solucion (`neo4j_<bloque>.py`) o el scaffold
(`neo4j_<bloque>_ex.py`), segun el contenido de la variable de entorno
`LAB_NEO4J` (lista separada por comas con los bloques desbloqueados).

Ejemplos:
    LAB_NEO4J=                       → todo scaffold (alumno)
    LAB_NEO4J=basic                  → basic resuelto, resto scaffold
    LAB_NEO4J=basic,intermediate     → basic+intermediate resueltos
    LAB_NEO4J=all                    → todo resuelto

El bloque ML (endpoints /api/analytics/ml/*) no se gatea aqui: solo lee
los parquets de modelos entrenados, asi que su disponibilidad la determina
si el alumno ha completado y ejecutado el correspondiente _ex.py.
"""

from fastapi import APIRouter

from infra.shared.lab_flags import import_block, read_lab_flag

router = APIRouter()


def _unlocked(env_var: str) -> set[str]:
    raw = read_lab_flag(env_var).strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return {"basic", "intermediate", "advanced", "supervised", "unsupervised", "graph_ml"}
    return {b.strip() for b in raw.split(",") if b.strip()}


_neo4j_unlocked = _unlocked("LAB_NEO4J")

_ROUTES = "src.web.routes"

# --- Bloques Cypher: solución si está desbloqueada y presente, si no scaffold ---
router.include_router(import_block(_ROUTES, "neo4j_basic", "basic" in _neo4j_unlocked).router)
router.include_router(import_block(_ROUTES, "neo4j_intermediate", "intermediate" in _neo4j_unlocked).router)
router.include_router(import_block(_ROUTES, "neo4j_advanced", "advanced" in _neo4j_unlocked).router)

# --- Endpoints ML (siempre incluidos; degradan si no hay parquets) ---
from src.web.routes import ml as _ml

router.include_router(_ml.router)


@router.get("/api/analytics/lab/status")
async def lab_status():
    """Estado actual del laboratorio: que bloques estan desbloqueados.

    El frontend puede llamar a este endpoint al arrancar para mostrar
    en el sidebar que partes estan en modo solucion vs ejercicio.
    """
    return {
        "neo4j": {
            "basic": "basic" in _neo4j_unlocked,
            "intermediate": "intermediate" in _neo4j_unlocked,
            "advanced": "advanced" in _neo4j_unlocked,
        },
        "ml": {
            "supervised": "supervised" in _unlocked("LAB_ML"),
            "unsupervised": "unsupervised" in _unlocked("LAB_ML"),
            "graph_ml": "graph_ml" in _unlocked("LAB_ML"),
        },
    }
