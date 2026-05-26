from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.hashtag import HashtagResponse, HashtagRecipeListResponse
from app.services.hashtag_service import HashtagService

router = APIRouter(prefix="/hashtags", tags=["hashtags"])


@router.get("/{tag_name}", response_model=HashtagResponse)
async def get_hashtag(
    tag_name: str,
    db: AsyncSession = Depends(get_db),
):
    service = HashtagService(db)
    hashtag = await service.get_hashtag(tag_name)
    if not hashtag:
        raise HTTPException(status_code=404, detail="Hashtag not found")
    return hashtag


@router.get("/{tag_name}/recipes", response_model=HashtagRecipeListResponse)
async def get_recipes_by_hashtag(
    tag_name: str,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = HashtagService(db)
    return await service.get_recipes_by_hashtag(tag_name, cursor, limit)
