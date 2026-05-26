import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_
from app.models.social import GroupBoard
from app.models.legacy_models import Recipe
from app.schemas.board import (
    BoardCreate,
    BoardUpdate,
    BoardItemUpdate,
    BoardResponse,
    BoardItemsResponse,
)


class BoardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_board(self, user_id: int, data: BoardCreate) -> BoardResponse:
        board = GroupBoard(user_id=user_id, board_name=data.board_name, compact_json={})
        self.db.add(board)
        await self.db.flush()
        await self.db.refresh(board)
        return BoardResponse(
            id=board.id,
            user_id=board.user_id,
            board_name=board.board_name,
            created_at=board.created_at,
        )

    async def update_board(self, board_id: int, user_id: int, data: BoardUpdate) -> BoardResponse | None:
        result = await self.db.execute(
            select(GroupBoard).where(and_(GroupBoard.id == board_id, GroupBoard.user_id == user_id))
        )
        board = result.scalar_one_or_none()
        if not board:
            return None

        board.board_name = data.board_name
        await self.db.flush()

        return BoardResponse(
            id=board.id,
            user_id=board.user_id,
            board_name=board.board_name,
            created_at=board.created_at,
        )

    async def delete_board(self, board_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(GroupBoard).where(and_(GroupBoard.id == board_id, GroupBoard.user_id == user_id))
        )
        board = result.scalar_one_or_none()
        if not board:
            return False

        await self.db.delete(board)
        await self.db.flush()
        return True

    async def update_board_items(self, board_id: int, user_id: int, data: BoardItemUpdate) -> bool:
        # Fetch recipe details for the new slot items (read, not a write).
        recipes_result = await self.db.execute(
            select(Recipe.id, Recipe.title, Recipe.slug)
            .where(Recipe.id.in_(data.recipe_ids))
        )
        recipe_map = {r.id: {"recipe_id": r.id, "title": r.title, "slug": r.slug}
                      for r in recipes_result}
        slot_data = [recipe_map[rid] for rid in data.recipe_ids if rid in recipe_map]

        # Single UPDATE: jsonb_set preserves other slots untouched.
        update_result = await self.db.execute(
            text("""
                UPDATE group_boards
                SET compact_json = jsonb_set(
                    COALESCE(compact_json, '{}'),
                    ARRAY[:slot],
                    :slot_data::jsonb
                )
                WHERE id = :board_id AND user_id = :user_id
                RETURNING id
            """),
            {
                "slot": data.slot,
                "slot_data": json.dumps(slot_data),
                "board_id": board_id,
                "user_id": user_id,
            }
        )
        await self.db.flush()
        return update_result.scalar_one_or_none() is not None

    async def get_board_items(self, board_id: int, user_id: int) -> BoardItemsResponse | None:
        result = await self.db.execute(
            select(GroupBoard.compact_json)
            .where(and_(GroupBoard.id == board_id, GroupBoard.user_id == user_id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        data = row or {}
        return BoardItemsResponse(
            tonight=data.get("tonight", []),
            this_week=data.get("this_week", []),
            later=data.get("later", []),
        )

    async def list_boards(self, user_id: int) -> list[BoardResponse]:
        result = await self.db.execute(
            select(GroupBoard)
            .where(GroupBoard.user_id == user_id)
            .order_by(GroupBoard.id.desc())
        )
        boards = result.scalars().all()

        return [
            BoardResponse(
                id=board.id,
                user_id=board.user_id,
                board_name=board.board_name,
                created_at=board.created_at,
            )
            for board in boards
        ]
