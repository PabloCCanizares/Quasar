"""Quasar Hub — la app central del ecosistema.

Tres responsabilidades:
  - Explicar:   landing con la narrativa + tarjetas de las apps.
  - Navegar:    enlaces a las 3 apps con indicador online en vivo.
  - Configurar: panel de profesor para desbloquear/bloquear bloques.
  - Onboarding: guía de primeros pasos.

No tiene base de datos ni Spark — solo orquesta y explica.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.config import APPS
from src.web.routes import status, control

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

app = FastAPI(
    title="Quasar Hub",
    description="Puerta de entrada del ecosistema Quasar.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status.router)
app.include_router(control.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "hub"}


@app.get("/api/hub/catalog")
async def catalog():
    """Catálogo estático de las apps (para la landing)."""
    return {
        "apps": [
            {
                "key": k,
                "name": m["name"],
                "tagline": m["tagline"],
                "description": m["description"],
                "url_public": m["url_public"],
                "color": m["color"],
                "flags": m["flags"],
            }
            for k, m in APPS.items()
        ]
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(TEMPLATES_DIR / "index.html"))
