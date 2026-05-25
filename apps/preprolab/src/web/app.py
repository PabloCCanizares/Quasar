"""PreproLab — FastAPI app esqueleto.

En Fase 1 solo expone:
  - /api/health
  - /api/preprolab/lab/status

Los bloques (eda, missing, outliers, integration, transform, normalize,
reduce_dim, reduce_inst) se irán añadiendo en fases posteriores.

Sirve un SPA mínimo en / con tabs vacíos por bloque para que el alumno vea
desde el primer arranque la estructura del laboratorio.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.web.database import get_async_client, get_db
from src.web.routes import analytics

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ping a Mongo al arrancar (lifespan classic FastAPI).
    client = get_async_client()
    await client.admin.command("ping")
    # No creamos colecciones aún — se irán creando cuando los bloques las usen.
    yield
    client.close()


app = FastAPI(
    title="PreproLab",
    description="Tema 5 — preprocesamiento clásico sobre flota de robots.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(analytics.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "preprolab"}


# Static y SPA
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(TEMPLATES_DIR / "index.html"))
