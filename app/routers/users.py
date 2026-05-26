from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas.user import UserProfileResponse, AvatarUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    profile = await service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.put("/me/avatar", status_code=204)
async def update_avatar(
    data: AvatarUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = UserService(db)
    success = await service.update_avatar(user_id, data.url)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
