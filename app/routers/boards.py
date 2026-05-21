from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas.board import (
    BoardCreate,
    BoardUpdate,
    BoardItemUpdate,
    BoardResponse,
    BoardItemsResponse
)
from app.services.board_service import BoardService

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post("", response_model=BoardResponse, status_code=201)
async def create_board(
    data: BoardCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = BoardService(db)
    board = await service.create_board(user_id, data)
    await db.commit()
    return board


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: int,
    data: BoardUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = BoardService(db)
    board = await service.update_board(board_id, user_id, data)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found or unauthorized")
    await db.commit()
    return board


@router.delete("/{board_id}", status_code=204)
async def delete_board(
    board_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = BoardService(db)
    success = await service.delete_board(board_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Board not found or unauthorized")
    await db.commit()


@router.get("", response_model=list[BoardResponse])
async def list_boards(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = BoardService(db)
    return await service.list_boards(user_id)


@router.put("/{board_id}/items", status_code=204)
async def update_board_items(
    board_id: int,
    data: BoardItemUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = BoardService(db)
    success = await service.update_board_items(board_id, user_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Board not found or unauthorized")
    await db.commit()


@router.get("/{board_id}/items", response_model=BoardItemsResponse)
async def get_board_items(
    board_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = BoardService(db)
    items = await service.get_board_items(board_id, user_id)
    if not items:
        raise HTTPException(status_code=404, detail="Board not found or unauthorized")
    return items
