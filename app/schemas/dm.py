from pydantic import BaseModel
from datetime import datetime


class ConversationStartRequest(BaseModel):
    recipient_id: int


class ConversationResponse(BaseModel):
    id: int
    participant_ids: list[int]
    last_message_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
