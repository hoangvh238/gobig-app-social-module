from pydantic import BaseModel
from datetime import datetime


class ActivityResponse(BaseModel):
    id: int
    user_id: int
    actor_id: int
    action_type: str
    payload_json: dict
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityListResponse(BaseModel):
    activities: list[ActivityResponse]
    next_cursor: int | None = None
