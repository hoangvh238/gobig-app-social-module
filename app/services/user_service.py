import hashlib
import hmac

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.legacy_models import User
from app.schemas.user import UserProfileResponse


def hash_streak(streak_count: int) -> str:
    """HMAC-SHA256 of streak_count. Raw count never leaves this function."""
    return hmac.new(
        settings.streak_secret.encode(),
        str(streak_count).encode(),
        hashlib.sha256,
    ).hexdigest()


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_profile(self, user_id: int) -> UserProfileResponse | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        return UserProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            avatar_url=user.avatar_url,
            follower_count=user.follower_count,
            following_count=user.following_count,
            recipe_count=user.recipe_count,
            streak_hash=user.streak_hash,
        )

    async def update_avatar(self, user_id: int, url: str) -> bool:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        user.avatar_url = url
        await self.db.flush()
        return True

    async def sync_streak(self, user_id: int, streak_count: int) -> str | None:
        """Hash streak_count, persist hash, return hash only — raw count is never stored or returned."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        h = hash_streak(streak_count)
        user.streak_hash = h
        await self.db.flush()
        return h
