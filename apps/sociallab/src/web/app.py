from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.web.database import get_async_client, get_db
from src.web.routes import analytics, interactions, posts, users

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_async_client()
    await client.admin.command("ping")

    db = get_db()
    await db.users.create_index("username")
    await db.posts.create_index([("created_at", -1)])
    await db.posts.create_index("user_id")
    await db.posts.create_index("hashtags")
    await db.likes.create_index([("user_id", 1), ("post_id", 1)], unique=True)
    await db.follows.create_index([("follower_id", 1), ("following_id", 1)], unique=True)
    await db.events.create_index([("created_at", -1)])

    yield
    client.close()


app = FastAPI(
    title="SocialLab",
    description="Twitter pedagógico — arquitectura de datos masivos",
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
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(interactions.router)
app.include_router(analytics.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/hashtags/trending")
async def trending_hashtags(limit: int = 10):
    """Top hashtags agregados desde la colección hashtag_trends."""
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": "$hashtag",
            "post_count": {"$sum": "$post_count"},
            "unique_users": {"$sum": "$unique_users"},
        }},
        {"$sort": {"post_count": -1}},
        {"$limit": limit},
        {"$project": {"hashtag": "$_id", "post_count": 1, "unique_users": 1, "_id": 0}},
    ]
    results = []
    async for doc in db.hashtag_trends.aggregate(pipeline):
        results.append(doc)
    return results


# Static files and SPA
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(TEMPLATES_DIR / "index.html"))
