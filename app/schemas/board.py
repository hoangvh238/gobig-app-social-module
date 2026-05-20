from pydantic import BaseModel, Field
from datetime import datetime


class BoardCreate(BaseModel):
    board_name: str = Field(min_length=1, max_length=200)


class BoardUpdate(BaseModel):
    board_name: str = Field(min_length=1, max_length=200)


class BoardItemUpdate(BaseModel):
    slot: str = Field(pattern="^(tonight|this_week|later)$")
    recipe_ids: list[int] = Field(max_length=50)


class BoardResponse(BaseModel):
    id: int
    user_id: int
    board_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class BoardItemsResponse(BaseModel):
    tonight: list[dict]
    this_week: list[dict]
    later: list[dict]
