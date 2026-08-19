"""Estado de la emisión de telemetría.

No es un ejercicio: siempre está disponible, como el `overview` de PreproLab
o el `corpus_stats` de LLM Lab. Sirve para que la web pueda decir si hay
datos y qué contienen antes de empezar a trabajar con ellos.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.config import RAW_PATH

router = APIRouter(prefix="/api/streamlab/emision", tags=["streamlab-emision"])


def _manifiesto() -> dict | None:
    ruta = Path(RAW_PATH) / "_emision.json"
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


@router.get("/status")
async def status() -> dict:
    """¿Hay telemetría emitida? Cuánta, de cuándo, y con qué problemas."""
    man = _manifiesto()
    lotes = sorted(Path(RAW_PATH).glob("lote-*.json"))
    if man is None:
        return {
            "emitido": False,
            "lotes_en_disco": len(lotes),
            "hint": "Ejecuta `./lab.sh streamlab emit` para generar telemetría.",
        }
    return {
        "emitido": True,
        "lotes_en_disco": len(lotes),
        **man,
    }


@router.get("/lote/{indice}")
async def lote(indice: int, limite: int = 20) -> dict:
    """Asoma unas cuantas lecturas de un lote concreto.

    Útil para ver con los propios ojos que dentro de un lote las lecturas no
    vienen ordenadas por ts_evento, que es de donde arranca todo lo demás.
    """
    ruta = Path(RAW_PATH) / f"lote-{indice:04d}.json"
    if not ruta.exists():
        raise HTTPException(404, detail=f"No existe el lote {indice}")
    lecturas = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                lecturas.append(json.loads(linea))
    muestra = lecturas[: max(1, min(limite, 200))]
    ordenado = [r["ts_evento"] for r in muestra] == sorted(r["ts_evento"] for r in muestra)
    return {
        "lote": indice,
        "lecturas": len(lecturas),
        "viene_ordenado": ordenado,
        "muestra": muestra,
    }
