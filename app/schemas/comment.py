from pydantic import BaseModel, Field
from datetime import datetime


class CommentCreate(BaseModel):
    recipe_id: int
    parent_id: int | None = None
    content: str = Field(min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    user_id: int
    recipe_id: int
    parent_id: int | None
    content: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    user_name: str | None = None
    user_avatar_id: int | None = None
    reply_count: int = 0

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    next_cursor: int | None = None
