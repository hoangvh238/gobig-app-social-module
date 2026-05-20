from pydantic import BaseModel, Field
from datetime import datetime


class CollectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    offline_sync: bool = False


class CollectionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    offline_sync: bool | None = None


class CollectionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    offline_sync: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionMinimalResponse(BaseModel):
    id: int
    title: str
    image_url: str | None
    ingredient_summary: str | None


class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse | CollectionMinimalResponse]
    next_cursor: int | None = None


class CollectionItemAdd(BaseModel):
    recipe_id: int
    notes: str | None = None
