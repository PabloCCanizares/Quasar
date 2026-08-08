from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str
    display_name: str
    email: str
    bio: str = ""
    group_id: str | None = None


class User(BaseModel):
    id: str = Field(alias="_id")
    username: str
    display_name: str
    email: str
    bio: str = ""
    avatar_url: str = ""
    group_id: str | None = None
    origin: Literal["seed", "live"] = "live"
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
