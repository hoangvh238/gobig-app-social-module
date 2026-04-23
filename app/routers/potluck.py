"""
Potluck social endpoints.
Social state in potluck_social:{session_id} — never touches core potluck:{session_id}.
Ping creates DM — never creates live room.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.potluck import (
    PotluckSocialStateRequest, PotluckSocialStateResponse,
    RSVPRequest, RSVPResponse,
    BuddySuggestRequest, BuddySuggestResponse,
    PotluckPingRequest, PotluckPingResponse,
)
from app.services.potluck_service import PotluckService

router = APIRouter()


def _extract_user_id(x_user_id: int = Header(...)) -> int:
    return x_user_id


@router.post("/potluck/state", response_model=PotluckSocialStateResponse)
async def set_potluck_state(
    request: PotluckSocialStateRequest,
    user_id: int = Depends(_extract_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create or update potluck social state."""
    return await PotluckService.set_state(user_id, request, db)


@router.get("/potluck/state/{session_id}", response_model=PotluckSocialStateResponse)
async def get_potluck_state(session_id: str):
    """Read potluck social state."""
    state = await PotluckService.get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


@router.post("/potluck/rsvp", response_model=RSVPResponse)
async def rsvp(
    request: RSVPRequest,
    user_id: int = Depends(_extract_user_id),
    db: AsyncSession = Depends(get_db),
):
    """RSVP to a potluck session."""
    return await PotluckService.rsvp(user_id, request, db)


@router.post("/potluck/suggest-buddies", response_model=BuddySuggestResponse)
async def suggest_buddies(
    request: BuddySuggestRequest,
    user_id: int = Depends(_extract_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Cook-buddy suggestions via hashed inventory compatibility + follow graph.
    No raw inventory data accessed.
    """
    return await PotluckService.suggest_buddies(user_id, request, db)


@router.post("/potluck/ping", response_model=PotluckPingResponse)
async def potluck_ping(
    request: PotluckPingRequest,
    user_id: int = Depends(_extract_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a DM ping to a user about a potluck.
    Creates a message — NEVER creates a live room.
    """
    return await PotluckService.ping(user_id, request, db)
