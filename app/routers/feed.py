from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.feed import FeedEnrichRequest, FeedEnrichResponse
from app.services.feed_service import FeedService

router = APIRouter()


@router.post("/feed/enrich", response_model=FeedEnrichResponse)
async def enrich_feed(
    request: FeedEnrichRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Enrich feed with social metadata (likes, comments, is_liked, is_saved).

    **IMPORTANT**: This endpoint annotates only, never reorders
    The response maintains the exact same order as the input device_ranked_ids.

    Input:
    - device_ranked_ids: List of recipe IDs (max 50) in device-ranked order
    - emotion_context: Emotion context for caching (lazy_night, date_night, family_chaos, default)
    - taste_profile_hash: Optional taste profile hash for personalization
    - inventory_hash: Optional inventory hash for filtering
    - frugal_mode: Filter to budget-friendly recipes only
    - user_id: Optional user ID for personalized data (is_liked, is_saved)

    Output:
    - items: Enriched recipe metadata in the same order as input
    """
    items = await FeedService.enrich_feed(
        device_ranked_ids=request.device_ranked_ids,
        emotion_context=request.emotion_context,
        taste_profile_hash=request.taste_profile_hash,
        inventory_hash=request.inventory_hash,
        frugal_mode=request.frugal_mode,
        user_id=request.user_id,
        db=db
    )
    return FeedEnrichResponse(items=items)
