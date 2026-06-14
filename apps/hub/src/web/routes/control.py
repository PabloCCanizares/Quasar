"""Control del laboratorio: desbloquear/bloquear bloques desde la web.

Mecanismo:
  1. Edita la variable LAB_* en el .env.docker montado (mismo archivo que
     usa lab.sh por CLI).
  2. Reinicia el contenedor de la app vía el Docker socket. La app, al
     re-arrancar, lee el flag actualizado del archivo (infra.shared.lab_flags)
     y re-evalúa qué bloques sirve como solución vs scaffold.

Requiere que el Hub tenga montado /var/run/docker.sock y el .env.docker
(rutas en config). Es un panel de profesor para un laboratorio local —
el control de contenedores es intencional.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import APPS, ENV_FILE

router = APIRouter(prefix="/api/hub", tags=["hub-control"])


class FlagChange(BaseModel):
    app: str          # clave de APPS (sociallab/preprolab/llmprep)
    flag: str         # nombre de la variable (LAB_PREPROLAB, LAB_NEO4J, ...)
    block: str        # bloque a tocar (missing, basic, ...)
    action: str       # "unlock" | "lock"


def _valid_blocks(app: str, flag: str) -> list[str]:
    meta = APPS.get(app)
    if not meta or flag not in meta["flags"]:
        return []
    return meta["flags"][flag]


def _edit_flag(flag: str, block: str, action: str) -> str:
    """Edita la línea FLAG= en el .env.docker. Devuelve el nuevo valor."""
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


def _restart_container(container: str) -> bool:
    """Reinicia un contenedor por nombre vía el Docker socket."""
    try:
        import docker
        client = docker.from_env()
        client.containers.get(container).restart(timeout=10)
        return True
    except Exception as e:
        raise HTTPException(503, detail=f"No pude reiniciar {container}: {e}")


@router.post("/flag")
async def set_flag(change: FlagChange) -> dict:
    """Desbloquea o bloquea un bloque y reinicia la app correspondiente."""
    meta = APPS.get(change.app)
    if not meta:
        raise HTTPException(404, detail=f"App desconocida: {change.app}")
    if change.flag not in meta["flags"]:
        raise HTTPException(400, detail=f"Flag {change.flag} no pertenece a {change.app}")
    if change.block not in _valid_blocks(change.app, change.flag):
        raise HTTPException(400, detail=f"Bloque {change.block} no válido para {change.flag}")

    new_value = _edit_flag(change.flag, change.block, change.action)
    _restart_container(meta["container"])

    return {
        "app": change.app,
        "flag": change.flag,
        "new_value": new_value or "(vacío)",
        "block": change.block,
        "action": change.action,
        "restarted": meta["container"],
        "note": "La app se está reiniciando (~3-5s). Recarga su estado en unos segundos.",
    }


@router.get("/flags")
async def current_flags() -> dict:
    """Devuelve el valor actual de cada flag LAB_* leído del .env.docker."""
    path = Path(ENV_FILE)
    flags: dict[str, str] = {}
    if path.exists():
        content = path.read_text(encoding="utf-8")
        for app_meta in APPS.values():
            for flag in app_meta["flags"]:
                m = re.search(rf'^{flag}=(.*)$', content, re.MULTILINE)
                flags[flag] = m.group(1).strip() if m else ""
    return {"flags": flags, "env_file": ENV_FILE}
