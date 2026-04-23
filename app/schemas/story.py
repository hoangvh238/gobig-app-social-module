from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal


class StoryType(str, Enum):
    cooking_moment = "cooking_moment"
    prep_pack = "prep_pack"
    challenge_entry = "challenge_entry"


# ── Confirm (after client uploads to /api/upload) ───────────────

class StoryConfirmRequest(BaseModel):
    url: str = Field(..., description="Full B2 URL from /api/upload response")
    key: str = Field(..., description="Object key from /api/upload response")
    size: int = Field(..., gt=0, le=52428800, description="File size in bytes (max 50MB)")
    mimetype: str = Field(..., description="MIME type from /api/upload response")
    emotion_preset: str | None = None
    challenge_id: int | None = None
    recipe_ids: list[int] = Field(default_factory=list, max_length=10)


class StoryConfirmResponse(BaseModel):
    story_id: int
    status: Literal["confirmed"] = "confirmed"


# ── TasteSearch ──────────────────────────────────────────────────────

class TasteSearchParams(BaseModel):
    q: str = Field(..., min_length=1, max_length=200)
    emotion_preset: str | None = None
    challenge_type: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class StorySearchHit(BaseModel):
    story_id: int
    user_id: int
    story_type: StoryType
    url: str
    key: str
    emotion_preset: str | None
    challenge_type: str | None
    score: float
    created_at: datetime


class TasteSearchResponse(BaseModel):
    results: list[StorySearchHit]
    total: int


# ── Story detail / feed ──────────────────────────────────────────────

class StoryDetail(BaseModel):
    id: int
    user_id: int
    url: str
    key: str
    size: int
    mimetype: str
    story_type: StoryType
    emotion_preset: str | None
    challenge_type: str | None
    time_preference: str | None
    recipe_ids: list[int] = []
    status: str
    expires_at: datetime
    created_at: datetime


class StoryFeedResponse(BaseModel):
    stories: list[StoryDetail]
    has_more: bool
