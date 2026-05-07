from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.models.interaction import Like, Follow
from src.web.database import get_db, neo4j_write

router = APIRouter(prefix="/api", tags=["interactions"])
db = get_db()


# --- Likes ---

@router.post("/posts/{post_id}/like", response_model=Like, status_code=201)
async def like_post(post_id: str, user_id: str):
    post = await db.posts.find_one({"_id": post_id})
    if not post:
        raise HTTPException(404, "Post not found")

    existing = await db.likes.find_one({"user_id": user_id, "post_id": post_id})
    if existing:
        raise HTTPException(409, "Already liked")

    like = Like(
        _id=f"lk_{uuid4().hex[:8]}",
        user_id=user_id,
        post_id=post_id,
    )
    doc = like.model_dump(by_alias=True)
    await db.likes.insert_one(doc)
    await db.posts.update_one({"_id": post_id}, {"$inc": {"likes_count": 1}})

    await _log_event("like", user_id, post_id)
    return doc


@router.delete("/posts/{post_id}/like", status_code=204)
async def unlike_post(post_id: str, user_id: str):
    result = await db.likes.delete_one({"user_id": user_id, "post_id": post_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Like not found")
    await db.posts.update_one({"_id": post_id}, {"$inc": {"likes_count": -1}})
    await _log_event("unlike", user_id, post_id)


@router.get("/posts/{post_id}/likes", response_model=list[Like])
async def get_post_likes(post_id: str):
    cursor = db.likes.find({"post_id": post_id})
    return [doc async for doc in cursor]


# --- Follows ---

@router.post("/users/{target_id}/follow", response_model=Follow, status_code=201)
async def follow_user(target_id: str, user_id: str):
    if user_id == target_id:
        raise HTTPException(400, "Cannot follow yourself")

    target = await db.users.find_one({"_id": target_id})
    if not target:
        raise HTTPException(404, "User not found")

    existing = await db.follows.find_one({"follower_id": user_id, "following_id": target_id})
    if existing:
        raise HTTPException(409, "Already following")

    follow = Follow(
        _id=f"fw_{uuid4().hex[:8]}",
        follower_id=user_id,
        following_id=target_id,
    )
    doc = follow.model_dump(by_alias=True)
    await db.follows.insert_one(doc)

    await db.users.update_one({"_id": user_id}, {"$inc": {"following_count": 1}})
    await db.users.update_one({"_id": target_id}, {"$inc": {"followers_count": 1}})

    await _log_event("follow", user_id, target_id)

    # Sync to Neo4j (best-effort)
    neo4j_write("""
        MERGE (a:User {id: $follower})
        MERGE (b:User {id: $following})
        MERGE (a)-[:FOLLOWS]->(b)
    """, {"follower": user_id, "following": target_id})

    return doc


@router.delete("/users/{target_id}/follow", status_code=204)
async def unfollow_user(target_id: str, user_id: str):
    result = await db.follows.delete_one({"follower_id": user_id, "following_id": target_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Follow not found")

    await db.users.update_one({"_id": user_id}, {"$inc": {"following_count": -1}})
    await db.users.update_one({"_id": target_id}, {"$inc": {"followers_count": -1}})

    await _log_event("unfollow", user_id, target_id)

    # Sync to Neo4j (best-effort)
    neo4j_write("""
        MATCH (a:User {id: $follower})-[f:FOLLOWS]->(b:User {id: $following})
        DELETE f
    """, {"follower": user_id, "following": target_id})


@router.get("/users/{user_id}/followers", response_model=list[Follow])
async def get_followers(user_id: str):
    cursor = db.follows.find({"following_id": user_id})
    return [doc async for doc in cursor]


@router.get("/users/{user_id}/following", response_model=list[Follow])
async def get_following(user_id: str):
    cursor = db.follows.find({"follower_id": user_id})
    return [doc async for doc in cursor]


# --- Hashtag search ---

@router.get("/hashtags/{tag}/posts")
async def posts_by_hashtag(tag: str, skip: int = 0, limit: int = 50):
    cursor = (
        db.posts.find({"hashtags": tag.lower()})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def _log_event(event_type: str, actor_id: str, target_id: str | None):
    await db.events.insert_one({
        "_id": f"ev_{uuid4().hex[:8]}",
        "event_type": event_type,
        "actor_id": actor_id,
        "target_id": target_id,
        "payload": {},
        "created_at": datetime.now(timezone.utc),
    })
