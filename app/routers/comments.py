from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse, CommentListResponse
from app.services.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("", response_model=CommentResponse, status_code=201)
async def create_comment(
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CommentService(db)
    comment = await service.create_comment(user_id, data)
    await db.commit()
    return comment


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CommentService(db)
    comment = await service.update_comment(comment_id, user_id, data)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found or unauthorized")
    await db.commit()
    return comment


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CommentService(db)
    success = await service.delete_comment(comment_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found or unauthorized")
    await db.commit()


@router.get("", response_model=CommentListResponse)
async def list_comments(
    recipe_id: int = Query(...),
    cursor: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = CommentService(db)
    return await service.list_comments(recipe_id, cursor, limit)


@router.get("/{parent_id}/replies", response_model=CommentListResponse)
async def list_replies(
    parent_id: int,
    cursor: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = CommentService(db)
    return await service.list_replies(parent_id, cursor, limit)


@router.post("/{comment_id}/flag", status_code=204)
async def flag_comment(
    comment_id: int,
    reason: str = Query(..., min_length=1, max_length=500),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CommentService(db)
    success = await service.flag_comment(comment_id, user_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.commit()
