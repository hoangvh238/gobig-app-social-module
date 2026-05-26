from pydantic import BaseModel
from datetime import datetime


class LikeResponse(BaseModel):
    user_id: int
    recipe_id: int
    created_at: datetime
    is_liked: bool

    class Config:
        from_attributes = True
