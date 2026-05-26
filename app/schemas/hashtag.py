from pydantic import BaseModel
from datetime import datetime


class HashtagResponse(BaseModel):
    id: int
    name: str
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class HashtagRecipeListResponse(BaseModel):
    recipes: list[dict]
    next_cursor: str | None = None
