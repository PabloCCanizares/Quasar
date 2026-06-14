"""Control del laboratorio: configurar bloques + acciones operativas.

Dos familias de acciones, ambas vía el Docker socket:
  - Flags:    editar LAB_* en .env.docker + reiniciar la app (scaffold/solución).
  - Tareas:   ejecutar seed / etl / ingest dentro del contenedor de la app.

Es un panel de profesor para un laboratorio local; el control de
contenedores es intencional.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import APPS, ENV_FILE, app_block_keys

router = APIRouter(prefix="/api/hub", tags=["hub-control"])


# ============================================================
# Comandos operativos por app (se ejecutan dentro del contenedor)
# ============================================================
# detach=True para tareas largas (ETL Spark); el estado de datos del Hub
# reflejará el resultado cuando termine.
TASKS = {
    "sociallab": {
        "seed": (["python", "-m", "src.seed.generate_dirty_data"], False),
        "etl":  (["python", "-m", "src.spark.run_pipeline", "--all"], True),
    },
    "preprolab": {
        "seed": (["python", "-m", "src.seed.generate_robot_fleet"], False),
    },
    "llmprep": {
        "ingest": (["python", "-m", "src.ingest.generate_corpus"], False),
    },
}


# ============================================================
# Flags (scaffold / solución)
# ============================================================

class FlagChange(BaseModel):
    app: str
    flag: str
    block: str
    action: str  # unlock | lock


def _edit_flag(flag: str, block: str, action: str) -> str:
    path = Path(ENV_FILE)
    if not path.exists():
        raise HTTPException(500, detail=f"No encuentro el archivo de flags: {ENV_FILE}")
    content = path.read_text(encoding="utf-8")
    m = re.search(rf'^{flag}=(.*)$', content, re.MULTILINE)
    current = m.group(1).strip() if m else ""
    blocks = set() if not current else {b.strip() for b in current.split(",") if b.strip()}
    if action == "unlock":
        blocks.add(block)
    elif action == "lock":
        blocks.discard(block)
    else:
        raise HTTPException(400, detail="action debe ser unlock o lock")
    new_value = ",".join(sorted(blocks))
    if m:
        content = re.sub(rf'^{flag}=.*$', f'{flag}={new_value}', content, flags=re.MULTILINE)
    else:
        content += f"\n{flag}={new_value}\n"
    path.write_text(content, encoding="utf-8")
    return new_value


def _restart_container(container: str) -> None:
    try:
        import docker
        docker.from_env().containers.get(container).restart(timeout=10)
    except Exception as e:
        raise HTTPException(503, detail=f"No pude reiniciar {container}: {e}")


@router.post("/flag")
async def set_flag(change: FlagChange) -> dict:
    meta = APPS.get(change.app)
    if not meta:
        raise HTTPException(404, detail=f"App desconocida: {change.app}")
    if change.block not in app_block_keys(change.app, change.flag):
        raise HTTPException(400, detail=f"Bloque {change.block} no válido para {change.flag}")
    new_value = _edit_flag(change.flag, change.block, change.action)
    _restart_container(meta["container"])
    return {
        "app": change.app, "flag": change.flag, "new_value": new_value or "(vacío)",
        "block": change.block, "action": change.action, "restarted": meta["container"],
    }


@router.get("/flags")
async def current_flags() -> dict:
    path = Path(ENV_FILE)
    flags: dict[str, str] = {}
    if path.exists():
        content = path.read_text(encoding="utf-8")
        for meta in APPS.values():
            for b in meta["blocks"]:
                if b["flag"] not in flags:
                    m = re.search(rf'^{b["flag"]}=(.*)$', content, re.MULTILINE)
                    flags[b["flag"]] = m.group(1).strip() if m else ""
    return {"flags": flags, "env_file": ENV_FILE}


# ============================================================
# Tareas operativas (seed / etl / ingest)
# ============================================================

class AppRef(BaseModel):
    app: str


@router.post("/restart")
async def restart_app(ref: AppRef) -> dict:
    meta = APPS.get(ref.app)
    if not meta:
        raise HTTPException(404, detail=f"App desconocida: {ref.app}")
    _restart_container(meta["container"])
    return {"app": ref.app, "restarted": meta["container"]}


class TaskRun(BaseModel):
    app: str
    task: str  # seed | etl | ingest


@router.post("/run")
async def run_task(req: TaskRun) -> dict:
    meta = APPS.get(req.app)
    if not meta:
        raise HTTPException(404, detail=f"App desconocida: {req.app}")
    app_tasks = TASKS.get(req.app, {})
    if req.task not in app_tasks:
        raise HTTPException(400, detail=f"Tarea {req.task} no disponible en {req.app}")

    cmd, detach = app_tasks[req.task]
    try:
        import docker
        container = docker.from_env().containers.get(meta["container"])
        if detach:
            container.exec_run(cmd, detach=True)
            return {
                "app": req.app, "task": req.task, "detached": True,
                "note": "Tarea lanzada en segundo plano (puede tardar 1-2 min). "
                        "Refresca el Estado para ver el resultado.",
            }
        else:
            result = container.exec_run(cmd)
            output = result.output.decode("utf-8", errors="replace")
            return {
                "app": req.app, "task": req.task, "detached": False,
                "exit_code": result.exit_code,
                "output_tail": output[-1200:],
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, detail=f"No pude ejecutar {req.task} en {meta['container']}: {e}")
