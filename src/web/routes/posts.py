import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.models.post import Post, PostCreate
from src.web.database import get_db, neo4j_write

router = APIRouter(prefix="/api/posts", tags=["posts"])
db = get_db()

HASHTAG_RE = re.compile(r"#(\w+)")
MENTION_RE = re.compile(r"@(\w+)")


@router.get("/", response_model=list[Post])
async def list_posts(
    user_id: str | None = None,
    hashtag: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = {}
    if user_id:
        query["user_id"] = user_id
    if hashtag:
        query["hashtags"] = hashtag.lower().lstrip("#")
    cursor = db.posts.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [doc async for doc in cursor]


@router.get("/timeline/{user_id}", response_model=list[Post])
async def timeline(user_id: str, skip: int = 0, limit: int = 50):
    """Feed: posts de usuarios que sigue + los propios."""
    following_ids = []
    cursor = db.follows.find({"follower_id": user_id})
    async for doc in cursor:
        following_ids.append(doc["following_id"])
    following_ids.append(user_id)

    posts_cursor = (
        db.posts.find({"user_id": {"$in": following_ids}})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [doc async for doc in posts_cursor]


@router.get("/{post_id}", response_model=Post)
async def get_post(post_id: str):
    doc = await db.posts.find_one({"_id": post_id})
    if not doc:
        raise HTTPException(404, "Post not found")
    return doc


@router.post("/", response_model=Post, status_code=201)
async def create_post(user_id: str, body: PostCreate):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    # Extract hashtags and mentions from text
    hashtags = [h.lower() for h in HASHTAG_RE.findall(body.text)]
    mentions = MENTION_RE.findall(body.text)
    # Merge with explicitly provided ones
    all_hashtags = list(set(hashtags + [h.lower().lstrip("#") for h in body.hashtags]))
    all_mentions = list(set(mentions + body.mentions))

    post = Post(
        _id=f"p_{uuid4().hex[:8]}",
        user_id=user_id,
        username=user["username"],
        text=body.text,
        hashtags=all_hashtags,
        mentions=all_mentions,
        group_id=user.get("group_id"),
    )
    doc = post.model_dump(by_alias=True)
    await db.posts.insert_one(doc)

    # Increment user post count
    await db.users.update_one({"_id": user_id}, {"$inc": {"posts_count": 1}})

    # Log event
    await _log_event("post", user_id, post.id, {"text": body.text})

    # Sync hashtags to Neo4j (best-effort)
    for tag in all_hashtags:
        neo4j_write("""
            MERGE (u:User {id: $uid})
            MERGE (h:Hashtag {name: $tag})
            MERGE (u)-[:INTERESTED_IN]->(h)
        """, {"uid": user_id, "tag": tag})

    return doc


async def _log_event(event_type: str, actor_id: str, target_id: str | None, payload: dict):
    from datetime import datetime, timezone
    await db.events.insert_one({
        "_id": f"ev_{uuid4().hex[:8]}",
        "event_type": event_type,
        "actor_id": actor_id,
        "target_id": target_id,
        "payload": payload,
        "created_at": datetime.now(timezone.utc),
    })
