"""Lectura de flags de laboratorio (LAB_*) con prioridad al archivo montado.

Por qué leer de archivo y no solo de os.getenv:
  El Quasar Hub edita infra/compose/.env.docker para destapar/esconder
  bloques desde la web y luego REINICIA el contenedor de la app. Un
  `docker restart` reutiliza el contenedor (no re-lee env_file), así que
  el nuevo valor del flag NO llegaría como variable de entorno.

  La solución: cada app monta .env.docker como archivo (ruta en
  QUASAR_ENV_FILE) y lee el flag de ahí en cada arranque. Así, tras un
  simple restart, el proceso re-importa, re-evalúa el gating y ve el
  valor nuevo.

Fallback: si QUASAR_ENV_FILE no está o el archivo no existe, lee de
os.getenv (modo nativo / sin Hub).
"""

from __future__ import annotations

import os
from pathlib import Path


def read_lab_flag(var_name: str) -> str:
    """Devuelve el valor del flag `var_name` (str crudo, sin procesar).

    Orden de prioridad:
      1. Archivo en QUASAR_ENV_FILE (lo que edita el Hub).
      2. Variable de entorno os.getenv.
    """
    env_file = os.getenv("QUASAR_ENV_FILE", "").strip()
    if env_file:
        p = Path(env_file)
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith(f"{var_name}=") and not line.startswith("#"):
                        return line.split("=", 1)[1].strip()
            except OSError:
                pass
    return os.getenv(var_name, "")
