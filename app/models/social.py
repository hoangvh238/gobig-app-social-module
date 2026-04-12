from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean, ForeignKey, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.models.legacy_models import Base
import enum


class FollowStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    resolved = "resolved"


class ActivityType(str, enum.Enum):
    like = "like"
    comment = "comment"
    follow = "follow"
    mention = "mention"
    reply = "reply"


class MessageType(str, enum.Enum):
    text = "text"
    image = "image"
    recipe = "recipe"


class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="accepted")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    _parent_id: Mapped[int] = mapped_column("_parent_id", Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Hashtag(Base):
    __tablename__ = "hashtags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class RecipeHashtag(Base):
    __tablename__ = "recipe_hashtags"

    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    hashtag_id: Mapped[int] = mapped_column(Integer, ForeignKey("hashtags.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Block(Base):
    __tablename__ = "blocks"

    blocker_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Mute(Base):
    __tablename__ = "mutes"

    muter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    muted_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    reported_recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    reported_comment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    comment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    content: Mapped[str | None] = mapped_column(Text)
    recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class TrustedReviewer(Base):
    __tablename__ = "trusted_reviewers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class SocialChallenge(Base):
    __tablename__ = "social_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    hashtag: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    end_date: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class LiveRoom(Base):
    __tablename__ = "live_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class LiveParticipant(Base):
    __tablename__ = "live_participants"

    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("live_rooms.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class LiveRoomTemplate(Base):
    __tablename__ = "live_room_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    default_settings: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class GroupBoard(Base):
    __tablename__ = "group_boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class BoardItem(Base):
    __tablename__ = "board_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    board_id: Mapped[int] = mapped_column(Integer, ForeignKey("group_boards.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    added_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
