"""
Application-level signal payload schemas for SOC-E live rooms.
These ride on Tuan's WS signaling channel (T2-M3) — never create new WS endpoints here.
"""
from typing import Literal, Optional
from pydantic import BaseModel


class JoinRoomSignal(BaseModel):
    type: Literal["join_room"] = "join_room"
    room_id: int
    user_id: int
    role: str = "viewer"


class LeaveRoomSignal(BaseModel):
    type: Literal["leave_room"] = "leave_room"
    room_id: int
    user_id: int


class RaiseHandSignal(BaseModel):
    type: Literal["raise_hand"] = "raise_hand"
    room_id: int
    user_id: int


class HostControlsSignal(BaseModel):
    type: Literal["host_controls"] = "host_controls"
    room_id: int
    action: str  # mute_all | unmute_all | kick_user | end_room | promote_co_host
    target_user_id: Optional[int] = None


class EmotionReactionSignal(BaseModel):
    type: Literal["emotion_reaction"] = "emotion_reaction"
    room_id: int
    user_id: int
    reaction_type: str  # heart | fire | clap | laugh | wow
    batch_seq: Optional[int] = None  # set by batch writer, not by client
