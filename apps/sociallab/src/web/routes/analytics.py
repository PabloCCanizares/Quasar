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

# Qué se sirve de verdad, que no siempre coincide con el flag: si la solución
# no está en disco (copia de alumnos), import_block cae al scaffold aunque el
# flag diga lo contrario. El estado refleja la realidad, no la intención.
_neo4j_served: dict[str, bool] = {}

# --- Bloques Cypher: solución si está desbloqueada y presente, si no scaffold ---
for _bloque, _modulo in (("basic", "neo4j_basic"),
                         ("intermediate", "neo4j_intermediate"),
                         ("advanced", "neo4j_advanced")):
    _mod = import_block(_ROUTES, _modulo, _bloque in _neo4j_unlocked)
    router.include_router(_mod.router)
    _neo4j_served[_bloque] = not _mod.__name__.endswith("_ex")

# --- Endpoints ML (siempre incluidos; degradan si no hay parquets) ---
from src.web.routes import ml as _ml

router.include_router(_ml.router)


# Un modelo por bloque ML: si su módulo solución no está en disco, el bloque
# no puede servir solución por mucho que el flag lo pida. Los modelos se
# despachan en src/spark/models/run_all.py, no aquí, así que se comprueba la
# presencia del fichero en vez del módulo importado.
_ML_MODELOS = {
    "supervised": "spam_detector",
    "unsupervised": "user_clustering",
    "graph_ml": "follow_recommender",
}


def _ml_disponible(modelo: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(f"src.spark.models.{modelo}") is not None
    except (ImportError, ValueError):
        return False


@router.get("/api/analytics/lab/status")
async def lab_status():
    """Estado actual del laboratorio: que bloques sirven solucion.

    `neo4j` y `ml` dicen que se sirve realmente; `flagged` que pide el flag.
    Cuando difieren es que la solucion no esta disponible en esta copia: es
    lo que ve un alumno con la distribucion sin soluciones.
    """
    ml_unlocked = _unlocked("LAB_ML")
    return {
        "neo4j": dict(_neo4j_served),
        "ml": {
            bloque: (bloque in ml_unlocked) and _ml_disponible(modelo)
            for bloque, modelo in _ML_MODELOS.items()
        },
        "flagged": {
            "neo4j": {b: (b in _neo4j_unlocked)
                      for b in ("basic", "intermediate", "advanced")},
            "ml": {b: (b in ml_unlocked) for b in _ML_MODELOS},
        },
    }
