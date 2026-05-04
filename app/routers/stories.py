"""
Story endpoints — direct upload flow.
Client uploads to /api/upload → gets {url, key, size, mimetype} → calls /confirm
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.story import (
    StoryConfirmRequest, StoryConfirmResponse,
    TasteSearchParams, TasteSearchResponse,
    StoryDetail, StoryFeedResponse,
)
from app.services.story_service import StoryService

router = APIRouter()


def _extract_user_id(x_user_id: int = Header(...)) -> int:
    return x_user_id


def _extract_taste_tier(x_taste_tier: str = Header(default="basic")) -> str:
    if x_taste_tier not in ("basic", "advanced", "hyper"):
        return "basic"
    return x_taste_tier


@router.post("/stories/confirm", response_model=StoryConfirmResponse)
async def confirm_story(
    request: StoryConfirmRequest,
    user_id: int = Depends(_extract_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm story upload after client uploaded to /api/upload.
    Client provides {url, key, size, mimetype} from upload response.
    """
    return await StoryService.confirm(user_id, request, db)


@router.get("/stories/search", response_model=TasteSearchResponse)
async def search_stories(
    q: str = Query(..., min_length=1, max_length=200),
    emotion_preset: str | None = Query(default=None),
    challenge_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    taste_tier: str = Depends(_extract_taste_tier),
):
    """TasteSearch: fuzzy ES match + TasteProfile boost per tier."""
    params = TasteSearchParams(
        q=q,
        emotion_preset=emotion_preset,
        challenge_type=challenge_type,
        limit=limit,
        offset=offset,
    )
    return await StoryService.taste_search(params, taste_tier)


@router.get("/stories/feed", response_model=StoryFeedResponse)
async def story_feed(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user_id: int | None = Header(default=None, alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Get stories feed (confirmed, non-expired)."""
    return await StoryService.get_feed(user_id, limit, offset, db)


@router.get("/stories/{story_id}", response_model=StoryDetail)
async def get_story(
    story_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single confirmed story."""
    story = await StoryService.get_story(story_id, db)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story
