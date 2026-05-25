from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    text: str
    hashtags: list[str] = []
    mentions: list[str] = []


class Post(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    username: str
    text: str
    hashtags: list[str] = []
    mentions: list[str] = []
    likes_count: int = 0
    is_spam: bool = False
    origin: Literal["seed", "live"] = "live"
    group_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}
