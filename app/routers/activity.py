from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.activity import ActivityListResponse
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity", tags=["activity"])


def get_current_user_id() -> int:
    return 1


@router.get("/me", response_model=ActivityListResponse)
async def get_my_activities(
    cursor: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = ActivityService(db)
    return await service.get_user_activities(user_id, cursor, limit)
