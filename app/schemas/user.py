from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: int
    name: str | None
    email: str | None
    avatar_url: str | None
    follower_count: int
    following_count: int
    recipe_count: int
    streak_hash: str | None

    class Config:
        from_attributes = True


class AvatarUpdateRequest(BaseModel):
    url: str


class StreakSyncRequest(BaseModel):
    streak_count: int = Field(..., ge=0, description="Raw streak count — hashed server-side before storage")


class StreakSyncResponse(BaseModel):
    streak_hash: str
