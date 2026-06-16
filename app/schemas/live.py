from typing import Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CreateRoomRequest(BaseModel):
    recipe_id: Optional[int] = None
    potluck_id: Optional[str] = None
    room_type: Literal["personal", "group"] = "personal"
    template_id: Optional[int] = None
    emotion_preset: Optional[str] = None
    low_res_first: bool = False
    audio_only: bool = False


class LiveRoomResponse(BaseModel):
    id: int
    creator_id: int
    recipe_id: Optional[int] = None
    potluck_id: Optional[str] = None
    room_type: str
    status: str
    template_id: Optional[int] = None
    emotion_preset: Optional[str] = None
    low_res_first: bool
    audio_only: bool
    template_hashtags: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LiveRoomTemplateResponse(BaseModel):
    id: int
    name: str
    emotion_preset: Optional[str] = None
    default_slot_min: Optional[int] = None
    default_hashtags: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClipMarkerRequest(BaseModel):
    timestamp_s: int = Field(..., ge=0, description="Seconds from room start")
    label: str = Field(..., min_length=1, max_length=200)


class ClipMarkerResponse(BaseModel):
    id: int
    room_id: int
    user_id: int
    timestamp_s: int
    label: str
    created_at: datetime

    model_config = {"from_attributes": True}


_VALID_REACTIONS = frozenset({"heart", "fire", "clap", "laugh", "wow"})


class ReactionRequest(BaseModel):
    reaction_type: str = Field(..., max_length=50)
    payload: Optional[dict] = None

    @field_validator("reaction_type")
    @classmethod
    def _validate_reaction(cls, v: str) -> str:
        if v not in _VALID_REACTIONS:
            raise ValueError(f"reaction_type must be one of {sorted(_VALID_REACTIONS)}")
        return v


class InventoryResponse(BaseModel):
    room_id: int
    participant_count: int
    aggregated: None = None
    note: str = "Inventory aggregation pending Tuan's dish scorer API (T2-M3)"
