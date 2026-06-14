"""LLM Lab — FastAPI app (esqueleto Fase 12).

Expone /api/health y /api/llmprep/lab/status. Sirve un SPA con tabs por
bloque (clean, dedup, tokenize, train). Los bloques se irán implementando
en fases posteriores.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.web.database import get_async_client
from src.web.routes import analytics

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
    title="LLM Lab",
    description="Preparación de corpus para LLMs — limpieza, dedup, tokenización, nanoGPT.",
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "llmprep"}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(TEMPLATES_DIR / "index.html"))
