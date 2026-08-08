"""Control del laboratorio: configurar bloques + acciones operativas.

Dos familias de acciones, ambas vía el Docker socket:
  - Flags:    editar LAB_* en .env.docker + reiniciar la app (scaffold/solución).
  - Tareas:   ejecutar seed / etl / ingest dentro del contenedor de la app.

Es un panel para un laboratorio local; el control de contenedores es
intencional.

Sobre el token (QUASAR_TEACHER_TOKEN):
  Sin token configurado —el caso normal, cada alumno con su copia local—
  estas acciones están abiertas: es su propia instalación y debe poder
  alternar solución/ejercicio a su ritmo.

  Al definir QUASAR_TEACHER_TOKEN, las acciones de escritura piden la
  cabecera `X-Quasar-Token`. Sirve para una instalación compartida o una
  máquina de demo, donde no interesa que cualquiera toque los flags.

  Ojo con lo que este token NO hace: no protege las soluciones. Si los
  ficheros `<bloque>.py` están presentes, se leen desde el editor sin
  pasar por aquí. Lo que evita el acceso anticipado es distribuir a los
  alumnos una copia sin esos ficheros (ver tools/make_student_dist.sh).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.config import APPS, ENV_FILE, app_block_keys

router = APIRouter(prefix="/api/hub", tags=["hub-control"])


def _require_teacher(token: str | None) -> None:
    """Valida el token si hay uno configurado. Sin configurar, no exige nada."""
    expected = os.getenv("QUASAR_TEACHER_TOKEN", "").strip()
    if not expected:
        return
    if not token or token != expected:
        raise HTTPException(
            status_code=401,
            detail="Esta instalación está protegida: falta el token de profesor.",
        )


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
        "etl":  (["python", "-m", "src.spark.run_pipeline"], True),
    },
    "llmprep": {
        "ingest": (["python", "-m", "src.ingest.generate_corpus"], False),
        "etl":    (["python", "-m", "src.spark.run_pipeline"], True),
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
async def set_flag(
    change: FlagChange,
    x_quasar_token: str | None = Header(default=None),
) -> dict:
    _require_teacher(x_quasar_token)
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


@router.get("/auth")
async def auth_status(x_quasar_token: str | None = Header(default=None)) -> dict:
    """Si esta instalación pide token y si el que trae el navegador vale.

    Nunca devuelve el token; solo si hay protección y si la sesión actual
    ya está autorizada, para que la UI sepa cuándo pedirlo.
    """
    expected = os.getenv("QUASAR_TEACHER_TOKEN", "").strip()
    return {
        "protected": bool(expected),
        "authorized": (not expected) or (x_quasar_token == expected),
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
async def restart_app(
    ref: AppRef,
    x_quasar_token: str | None = Header(default=None),
) -> dict:
    _require_teacher(x_quasar_token)
    meta = APPS.get(ref.app)
    if not meta:
        raise HTTPException(404, detail=f"App desconocida: {ref.app}")
    _restart_container(meta["container"])
    return {"app": ref.app, "restarted": meta["container"]}


class TaskRun(BaseModel):
    app: str
    task: str  # seed | etl | ingest


@router.post("/run")
async def run_task(
    req: TaskRun,
    x_quasar_token: str | None = Header(default=None),
) -> dict:
    _require_teacher(x_quasar_token)
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
