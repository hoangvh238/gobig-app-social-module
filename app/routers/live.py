"""
Live room endpoints — SOC-E (L-M1-S + L-M2-S).

WebSocket/WebRTC/ICE/SDP/STUN/TURN config intentionally absent.
Signaling rides on Tuan's channel (T2-M3). Tier gate is an inline
header stub — swap the import for Tuan's @require_tier when T1-M4 ships.
is_blocked() comes from app/services/safety.py (S-M3 already live).
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_id
from app.database import get_db
from app.models.social import (
    LiveClipMarker,
    LiveParticipant,
    LiveRoom,
    LiveRoomTemplate,
)
from app.redis_client import redis_pool
from app.schemas.live import (
    ClipMarkerRequest,
    ClipMarkerResponse,
    CreateRoomRequest,
    InventoryResponse,
    LiveRoomResponse,
    LiveRoomTemplateResponse,
    ReactionRequest,
)
from app.services.safety import is_blocked

log = logging.getLogger(__name__)

router = APIRouter()

_REACTION_BUFFER_KEY = "live:reaction_buffer"


# ── tier stub (T1-M4 replacement target) ──────────────────────────────
def _get_user_tier(x_user_tier: str = Header(default="basic", alias="X-User-Tier")) -> str:
    """Reads tier from header injected by Tuan's auth gateway. Replace with T1-M4 import when ready."""
    if x_user_tier not in ("basic", "advanced", "hyper"):
        return "basic"
    return x_user_tier


# ── templates ──────────────────────────────────────────────────────────

@router.get("/live/templates", response_model=list[LiveRoomTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LiveRoomTemplate).order_by(LiveRoomTemplate.id))
    return result.scalars().all()


# ── room CRUD ──────────────────────────────────────────────────────────

@router.post("/live/rooms", response_model=LiveRoomResponse, status_code=201)
async def create_room(
    data: CreateRoomRequest,
    user_id: int = Depends(get_current_user_id),
    tier: str = Depends(_get_user_tier),
    db: AsyncSession = Depends(get_db),
):
    # T1-M4: tier gate for group hosting
    if data.room_type == "group" and tier == "basic":
        raise HTTPException(status_code=403, detail="Advanced tier required for group hosting")

    emotion_preset = data.emotion_preset
    template_hashtags = None

    if data.template_id is not None:
        tmpl_res = await db.execute(
            select(LiveRoomTemplate).where(LiveRoomTemplate.id == data.template_id)
        )
        tmpl = tmpl_res.scalar_one_or_none()
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if emotion_preset is None:
            emotion_preset = tmpl.emotion_preset
        template_hashtags = tmpl.default_hashtags

    room = LiveRoom(
        creator_id=user_id,
        recipe_id=data.recipe_id,
        potluck_id=data.potluck_id,
        room_type=data.room_type,
        status="scheduled",
        template_id=data.template_id,
        emotion_preset=emotion_preset,
        low_res_first=data.low_res_first,
        audio_only=data.audio_only,
    )
    db.add(room)
    await db.flush()

    host = LiveParticipant(room_id=room.id, user_id=user_id, role="host")
    db.add(host)
    await db.commit()
    await db.refresh(room)

    return LiveRoomResponse.model_validate(room).model_copy(update={"template_hashtags": template_hashtags})


@router.get("/live/rooms/{room_id}", response_model=LiveRoomResponse)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    room = await _get_room_or_404(room_id, db)
    return LiveRoomResponse.model_validate(room)


@router.post("/live/rooms/{room_id}/join", status_code=200)
async def join_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    room = await _get_room_or_404(room_id, db)

    if room.status == "ended":
        raise HTTPException(status_code=410, detail="Room has ended")

    # S-M3: block enforcement (is_blocked already live in safety.py)
    if await is_blocked(user_id, room.creator_id, db):
        raise HTTPException(status_code=403, detail="Blocked")

    # Upsert participant — re-join after leave is allowed
    existing = await db.execute(
        select(LiveParticipant).where(
            LiveParticipant.room_id == room_id,
            LiveParticipant.user_id == user_id,
            LiveParticipant.left_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is None:
        participant = LiveParticipant(room_id=room_id, user_id=user_id, role="viewer")
        db.add(participant)
        await db.commit()

    return {"room_id": room_id, "user_id": user_id, "status": "joined"}


@router.post("/live/rooms/{room_id}/leave", status_code=200)
async def leave_room(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_room_or_404(room_id, db)

    result = await db.execute(
        select(LiveParticipant).where(
            LiveParticipant.room_id == room_id,
            LiveParticipant.user_id == user_id,
            LiveParticipant.left_at.is_(None),
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=404, detail="Not in room")

    participant.left_at = datetime.now(timezone.utc)
    await db.commit()
    return {"room_id": room_id, "user_id": user_id, "status": "left"}


# ── inventory board ────────────────────────────────────────────────────

@router.get("/live/rooms/{room_id}/inventory", response_model=InventoryResponse)
async def get_inventory(
    room_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregate participant inventory via Tuan's dish scorer API.
    Stub until T2-M3 provides the dish scorer endpoint — returns participant count only.
    Zero raw inventory exposure by design.
    """
    await _get_room_or_404(room_id, db)

    count_result = await db.execute(
        select(func.count()).select_from(LiveParticipant).where(
            LiveParticipant.room_id == room_id,
            LiveParticipant.left_at.is_(None),
        )
    )
    participant_count = count_result.scalar_one()

    return InventoryResponse(room_id=room_id, participant_count=participant_count)


# ── reactions ──────────────────────────────────────────────────────────

@router.post("/live/rooms/{room_id}/reactions", status_code=202)
async def queue_reaction(
    room_id: int,
    data: ReactionRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue reaction to Redis buffer — zero per-reaction DB writes on hot path.
    Celery task flushes to live_reaction_events every 30 seconds.
    WS broadcast is Tuan's responsibility via T2-M3 signaling channel.
    """
    await _get_room_or_404(room_id, db)

    try:
        event = json.dumps({"room_id": room_id, "user_id": user_id, "reaction_type": data.reaction_type})
        await redis_pool.rpush(_REACTION_BUFFER_KEY, event)
    except Exception as exc:
        log.warning("live_reaction_buffer_push_failed", extra={"error": str(exc)})

    return {"queued": True, "room_id": room_id, "reaction_type": data.reaction_type}


# ── clip markers ───────────────────────────────────────────────────────

@router.post("/live/rooms/{room_id}/clip-marker", response_model=ClipMarkerResponse, status_code=201)
async def create_clip_marker(
    room_id: int,
    data: ClipMarkerRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_room_or_404(room_id, db)

    marker = LiveClipMarker(
        room_id=room_id,
        user_id=user_id,
        timestamp_s=data.timestamp_s,
        label=data.label,
    )
    db.add(marker)
    await db.commit()
    await db.refresh(marker)
    return ClipMarkerResponse.model_validate(marker)


@router.get("/live/rooms/{room_id}/clip-markers", response_model=list[ClipMarkerResponse])
async def list_clip_markers(
    room_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_room_or_404(room_id, db)

    result = await db.execute(
        select(LiveClipMarker)
        .where(LiveClipMarker.room_id == room_id)
        .order_by(LiveClipMarker.timestamp_s.asc())
    )
    return result.scalars().all()


# ── helpers ────────────────────────────────────────────────────────────

async def _get_room_or_404(room_id: int, db: AsyncSession) -> LiveRoom:
    result = await db.execute(select(LiveRoom).where(LiveRoom.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room
