from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas.like import LikeResponse
from app.services.like_service import LikeService

router = APIRouter(prefix="/likes", tags=["likes"])


@router.post("/{recipe_id}", response_model=LikeResponse)
async def toggle_like(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = LikeService(db)
    result = await service.toggle_like(user_id, recipe_id)
    await db.commit()
    return result


@router.get("/{recipe_id}/status")
async def get_like_status(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = LikeService(db)
    is_liked = await service.get_like_status(user_id, recipe_id)
    return {"is_liked": is_liked}
