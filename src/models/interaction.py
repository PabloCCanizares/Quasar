from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Like(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    post_id: str
    origin: Literal["seed", "live"] = "live"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class Follow(BaseModel):
    id: str = Field(alias="_id")
    follower_id: str
    following_id: str
    origin: Literal["seed", "live"] = "live"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class Event(BaseModel):
    """Evento genérico para el sync al data lake."""
    id: str = Field(alias="_id")
    event_type: Literal["post", "like", "unlike", "follow", "unfollow", "signup"]
    actor_id: str
    target_id: str | None = None
    payload: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}
