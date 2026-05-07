import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.models.user import User, UserCreate, UserUpdate
from src.web.database import get_db, neo4j_write

router = APIRouter(prefix="/api/users", tags=["users"])
db = get_db()


def clean_user_doc(doc: dict) -> dict:
    """Normalize dirty seed rows before FastAPI response validation."""
    if not doc:
        return doc
    username = doc.get("username") or "unknown"
    doc["username"] = username
    doc["display_name"] = doc.get("display_name") or username
    doc["email"] = doc.get("email") or f"{username}@missing.local"
    doc["bio"] = doc.get("bio") or ""
    doc["avatar_url"] = doc.get("avatar_url") or ""
    doc["followers_count"] = doc.get("followers_count") or 0
    doc["following_count"] = doc.get("following_count") or 0
    doc["posts_count"] = doc.get("posts_count") or 0
    return doc


@router.get("/", response_model=list[User])
async def list_users(
    origin: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = {}
    if origin:
        query["origin"] = origin
    if q:
        term = q.strip().lstrip("@")
        if term:
            safe = re.escape(term)
            search = {
                "$or": [
                    {"username": {"$regex": safe, "$options": "i"}},
                    {"display_name": {"$regex": safe, "$options": "i"}},
                    {"bio": {"$regex": safe, "$options": "i"}},
                ]
            }
            query = {"$and": [query, search]} if query else search

    cursor = (
        db.users.find(query)
        .sort([("followers_count", -1), ("posts_count", -1), ("username", 1)])
        .skip(skip)
        .limit(limit)
    )
    return [clean_user_doc(doc) async for doc in cursor]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str):
    doc = await db.users.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(404, "User not found")
    return clean_user_doc(doc)


@router.get("/by-username/{username}", response_model=User)
async def get_user_by_username(username: str):
    doc = await db.users.find_one({"username": username})
    if not doc:
        raise HTTPException(404, "User not found")
    return clean_user_doc(doc)


@router.post("/", response_model=User, status_code=201)
async def create_user(body: UserCreate):
    existing = await db.users.find_one({"username": body.username})
    if existing:
        raise HTTPException(409, "Username already taken")

    user = User(
        _id=f"u_{uuid4().hex[:8]}",
        **body.model_dump(),
    )
    doc = user.model_dump(by_alias=True)
    await db.users.insert_one(doc)

    # Sync to Neo4j (best-effort)
    neo4j_write("""
        MERGE (u:User {id: $id})
        SET u.username = $username,
            u.display_name = $name,
            u.origin = 'live',
            u.followers_count = 0,
            u.following_count = 0,
            u.posts_count = 0
    """, {"id": doc["_id"], "username": doc["username"],
          "name": doc.get("display_name", doc["username"])})

    return doc


@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: str, body: UserUpdate):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await db.users.find_one_and_update(
        {"_id": user_id},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(404, "User not found")
    return clean_user_doc(result)
