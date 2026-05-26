from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_
from app.models.social import Like
from app.models.legacy_models import Recipe, User
from app.schemas.like import LikeResponse
from app.services.activity_service import ActivityService


class LikeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def toggle_like(self, user_id: int, recipe_id: int) -> LikeResponse:
        # Advisory lock BEFORE the existence check to prevent TOCTOU races on like_count.
        # Serializes all like/unlike ops per recipe; different recipes are independent.
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": recipe_id}
        )

        result = await self.db.execute(
            select(Like).where(
                and_(Like.user_id == user_id, Like.recipe_id == recipe_id)
            )
        )
        existing_like = result.scalar_one_or_none()

        if existing_like:
            await self.db.delete(existing_like)
            await self.db.execute(
                text("UPDATE recipes SET like_count = GREATEST(like_count - 1, 0) WHERE id = :recipe_id"),
                {"recipe_id": recipe_id}
            )
            await self.db.flush()
            return LikeResponse(
                user_id=user_id,
                recipe_id=recipe_id,
                created_at=existing_like.created_at,
                is_liked=False
            )

        insert_result = await self.db.execute(
            text("""
                INSERT INTO likes (user_id, recipe_id, created_at)
                VALUES (:user_id, :recipe_id, NOW())
                ON CONFLICT (user_id, recipe_id) DO NOTHING
                RETURNING created_at
            """),
            {"user_id": user_id, "recipe_id": recipe_id}
        )
        inserted_at = insert_result.scalar_one_or_none()

        if inserted_at:
            await self.db.execute(
                text("UPDATE recipes SET like_count = like_count + 1 WHERE id = :recipe_id"),
                {"recipe_id": recipe_id}
            )
            user = await self.db.get(User, user_id)
            recipe = await self.db.get(Recipe, recipe_id)
            activity_service = ActivityService(self.db)
            await activity_service.create_activity(
                user_id=user_id,
                actor_id=user_id,
                action_type="like",
                payload_json={
                    "recipe_id": recipe_id,
                    "recipe_title": recipe.title if recipe else None,
                    "user_name": user.name if user else None,
                }
            )

        await self.db.flush()
        return LikeResponse(
            user_id=user_id,
            recipe_id=recipe_id,
            created_at=inserted_at or datetime.now(timezone.utc),
            is_liked=True
        )

    async def get_like_status(self, user_id: int, recipe_id: int) -> bool:
        result = await self.db.execute(
            select(Like).where(
                and_(
                    Like.user_id == user_id,
                    Like.recipe_id == recipe_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
