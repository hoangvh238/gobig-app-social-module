from enum import IntEnum
from pydantic import BaseModel, Field
from typing import Literal


class SlotDuration(IntEnum):
    fifteen = 15
    thirty = 30
    forty_five = 45


# ── Social State ─────────────────────────────────────────────────────

class PotluckSocialStateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    friends_only: bool = False
    invite_from_followers: bool = True
    slot_duration_min: SlotDuration = SlotDuration.thirty
    host_controls: dict = Field(default_factory=dict)


class PotluckSocialStateResponse(BaseModel):
    session_id: str
    friends_only: bool
    invite_from_followers: bool
    rsvp: dict[str, str]
    host_controls: dict
    slot_duration_min: int


# ── RSVP ─────────────────────────────────────────────────────────────

class RSVPRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    status: Literal["attending", "maybe", "declined"]


class RSVPResponse(BaseModel):
    session_id: str
    user_id: int
    status: str


# ── Cook-Buddy Suggestions ───────────────────────────────────────────

class BuddySuggestRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=30)


class BuddySuggestion(BaseModel):
    user_id: int
    display_name: str | None
    avatar_id: str | None  # Avatar URL or path
    compatibility_score: float
    mutual_follows: int
    combined_score: float


class BuddySuggestResponse(BaseModel):
    suggestions: list[BuddySuggestion]


# ── Potluck Ping (DM) ───────────────────────────────────────────────

class PotluckPingRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    target_user_ids: list[int] = Field(..., min_items=1, max_items=20)  # Support multiple users
    message: str = Field(..., min_length=1, max_length=500)


class PotluckPingResponse(BaseModel):
    session_id: str
    sent_to: list[int]  # User IDs that received the message
    failed: list[int]  # User IDs that failed (blocked/muted/self)
    message_ids: list[int]  # Message IDs created


# ── Invite Users ─────────────────────────────────────────────────────

class InviteUsersRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    user_ids: list[int] = Field(..., min_items=1, max_items=50)


class InviteUsersResponse(BaseModel):
    session_id: str
    invited: list[int]
    failed: list[int]
