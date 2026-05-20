from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.legacy_models import User
from app.schemas.user import UserProfileResponse, PresignedUrlResponse
import uuid


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_profile(self, user_id: int) -> UserProfileResponse | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        return UserProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            avatar_id=user.avatar_id,
            follower_count=user.follower_count,
            following_count=user.following_count,
            recipe_count=user.recipe_count,
            streak_hash=user.streak_hash
        )

    async def generate_avatar_presign(self, user_id: int) -> PresignedUrlResponse:
        avatar_id = int(str(uuid.uuid4().int)[:9])

        upload_url = f"https://storage.example.com/presign/{avatar_id}"

        return PresignedUrlResponse(
            upload_url=upload_url,
            avatar_id=avatar_id
        )

    async def update_avatar(self, user_id: int, avatar_id: int) -> bool:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        user.avatar_id = avatar_id
        await self.db.flush()
        return True
