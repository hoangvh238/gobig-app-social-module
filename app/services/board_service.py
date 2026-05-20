from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_
from app.models.social import GroupBoard, BoardItem
from app.models.legacy_models import Recipe
from app.schemas.board import (
    BoardCreate,
    BoardUpdate,
    BoardItemUpdate,
    BoardResponse,
    BoardItemsResponse
)


class BoardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_board(self, user_id: int, data: BoardCreate) -> BoardResponse:
        board = GroupBoard(
            user_id=user_id,
            board_name=data.board_name
        )
        self.db.add(board)
        await self.db.flush()
        await self.db.refresh(board)

        return BoardResponse(
            id=board.id,
            user_id=board.user_id,
            board_name=board.board_name,
            created_at=board.created_at
        )

    async def update_board(
        self,
        board_id: int,
        user_id: int,
        data: BoardUpdate
    ) -> BoardResponse | None:
        result = await self.db.execute(
            select(GroupBoard).where(
                and_(
                    GroupBoard.id == board_id,
                    GroupBoard.user_id == user_id
                )
            )
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
            created_at=board.created_at
        )

    async def delete_board(self, board_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(GroupBoard).where(
                and_(
                    GroupBoard.id == board_id,
                    GroupBoard.user_id == user_id
                )
            )
        )
        board = result.scalar_one_or_none()
        if not board:
            return False

        await self.db.delete(board)
        await self.db.flush()
        return True

    async def update_board_items(
        self,
        board_id: int,
        user_id: int,
        data: BoardItemUpdate
    ) -> bool:
        result = await self.db.execute(
            select(GroupBoard).where(
                and_(
                    GroupBoard.id == board_id,
                    GroupBoard.user_id == user_id
                )
            )
        )
        board = result.scalar_one_or_none()
        if not board:
            return False

        await self.db.execute(
            text("DELETE FROM board_items WHERE board_id = :board_id AND slot = :slot"),
            {"board_id": board_id, "slot": data.slot}
        )

        for idx, recipe_id in enumerate(data.recipe_ids):
            item = BoardItem(
                board_id=board_id,
                recipe_id=recipe_id,
                slot=data.slot,
                display_order=idx
            )
            self.db.add(item)

        await self.db.flush()
        return True

    async def get_board_items(
        self,
        board_id: int,
        user_id: int
    ) -> BoardItemsResponse | None:
        result = await self.db.execute(
            select(GroupBoard).where(
                and_(
                    GroupBoard.id == board_id,
                    GroupBoard.user_id == user_id
                )
            )
        )
        board = result.scalar_one_or_none()
        if not board:
            return None

        items_result = await self.db.execute(
            select(BoardItem, Recipe)
            .join(Recipe, BoardItem.recipe_id == Recipe.id)
            .where(BoardItem.board_id == board_id)
            .order_by(BoardItem.slot, BoardItem.display_order)
        )
        items_data = items_result.all()

        tonight = []
        this_week = []
        later = []

        for item, recipe in items_data:
            recipe_dict = {
                "recipe_id": recipe.id,
                "title": recipe.title,
                "slug": recipe.slug
            }

            if item.slot == "tonight":
                tonight.append(recipe_dict)
            elif item.slot == "this_week":
                this_week.append(recipe_dict)
            elif item.slot == "later":
                later.append(recipe_dict)

        return BoardItemsResponse(
            tonight=tonight,
            this_week=this_week,
            later=later
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
                created_at=board.created_at
            )
            for board in boards
        ]
