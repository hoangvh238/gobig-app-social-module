from pydantic import BaseModel, Field, field_validator
from typing import Literal


class FeedEnrichRequest(BaseModel):
    device_ranked_ids: list[str] = Field(..., max_length=50, description="Device-ranked recipe IDs (max 50)")
    emotion_context: Literal["lazy_night", "date_night", "family_chaos", "default"] = "default"
    taste_profile_hash: str | None = None
    inventory_hash: str | None = None
    frugal_mode: bool = False
    user_id: int | None = None

    @field_validator('device_ranked_ids')
    @classmethod
    def validate_max_length(cls, v):
        if len(v) > 50:
            raise ValueError('device_ranked_ids must contain at most 50 items')
        return v


class AuthorProfile(BaseModel):
    id: int
    name: str | None
    avatar_id: int | None
    follower_count: int


class RecipeSocialMeta(BaseModel):
    recipe_id: int
    title: str | None
    slug: str | None
    featured_image_id: int | None
    prep_time: int | None
    cook_time: int | None
    servings: int | None
    difficulty: str | None
    rating: float | None
    description: str | None
    author: AuthorProfile
    like_count: int
    comment_count: int
    is_liked: bool
    is_saved: bool
    tags: list[str] = []


class FeedEnrichResponse(BaseModel):
    items: list[RecipeSocialMeta]
