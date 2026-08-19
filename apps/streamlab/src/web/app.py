"""StreamLab — FastAPI app.

Fase 1 (esqueleto) expone:
  - /api/health
  - /api/streamlab/lab/status
  - el status de cada bloque (windows, late, state), aún en scaffold

Los bloques se implementan en las fases 3-5. Sirve un SPA mínimo en / con la
estructura del laboratorio para que se vea desde el primer arranque.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.web.database import get_async_client
from src.web.routes import analytics, demo, emision

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_async_client()
    await client.admin.command("ping")
    yield
    client.close()


app = FastAPI(
    title="StreamLab",
    description="Procesamiento en tiempo real sobre la telemetría de la flota.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router)
# Estado de la emisión: no es ejercicio, siempre disponible.
app.include_router(emision.router)
# Demo culminante (batch vs streaming): tampoco es ejercicio.
app.include_router(demo.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "streamlab"}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(TEMPLATES_DIR / "index.html"))
