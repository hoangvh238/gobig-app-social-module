from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Integer, String, Text, Boolean, ForeignKey, TIMESTAMP, Date,
    ARRAY, VARCHAR, BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.models.legacy_models import Base
import enum


class ReportStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    resolved = "resolved"
    dismissed = "dismissed"


class ActivityType(str, enum.Enum):
    like = "like"
    comment = "comment"
    follow = "follow"
    share = "share"
    mention = "mention"


class LiveRoomStatus(str, enum.Enum):
    scheduled = "scheduled"
    live = "live"
    ended = "ended"


class LiveParticipantRole(str, enum.Enum):
    host = "host"
    co_host = "co_host"
    viewer = "viewer"


class BoardItemSlot(str, enum.Enum):
    tonight = "tonight"
    this_week = "this_week"
    later = "later"


class StoryType(str, enum.Enum):
    cooking_moment = "cooking_moment"
    prep_pack = "prep_pack"
    challenge_entry = "challenge_entry"


class StoryStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class PotluckEventType(str, enum.Enum):
    rsvp = "rsvp"
    invite_sent = "invite_sent"
    buddy_suggested = "buddy_suggested"
    ping_sent = "ping_sent"
    state_updated = "state_updated"


# ── follows ──────────────────────────────────────────────────────────
# DDL: follower_id, following_id (composite PK), created_at
class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── likes ────────────────────────────────────────────────────────────
# DDL: user_id, recipe_id (composite PK), created_at
class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── comments ─────────────────────────────────────────────────────────
# DDL: id SERIAL, user_id, recipe_id, parent_id, content, is_deleted, created_at, updated_at
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


# ── collections ──────────────────────────────────────────────────────
# DDL: id SERIAL, user_id, title VARCHAR, description VARCHAR, offline_sync BOOLEAN, created_at, updated_at
class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    description: Mapped[str | None] = mapped_column(VARCHAR)
    offline_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── collection_items ─────────────────────────────────────────────────
# DDL: id VARCHAR PK, _order INTEGER, _parent_id FK, recipe_id FK, notes VARCHAR, added_at
class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[str] = mapped_column(VARCHAR, primary_key=True)
    _order: Mapped[int] = mapped_column("_order", Integer, nullable=False)
    _parent_id: Mapped[int] = mapped_column("_parent_id", Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    notes: Mapped[str | None] = mapped_column(VARCHAR)
    added_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── hashtags ─────────────────────────────────────────────────────────
# DDL: id SERIAL, name VARCHAR UNIQUE, usage_count, created_at
class Hashtag(Base):
    __tablename__ = "hashtags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR, nullable=False, unique=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── recipe_hashtags ──────────────────────────────────────────────────
# DDL: recipe_id, hashtag_id (composite PK), created_at
class RecipeHashtag(Base):
    __tablename__ = "recipe_hashtags"

    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    hashtag_id: Mapped[int] = mapped_column(Integer, ForeignKey("hashtags.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── blocks ───────────────────────────────────────────────────────────
# DDL: blocker_id, blocked_id (composite PK), created_at
class Block(Base):
    __tablename__ = "blocks"

    blocker_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── mutes ────────────────────────────────────────────────────────────
# DDL: muter_id, muted_id (composite PK), created_at
class Mute(Base):
    __tablename__ = "mutes"

    muter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    muted_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── reports ──────────────────────────────────────────────────────────
# DDL: id SERIAL, reporter_id, reported_user_id, reported_recipe_id,
#      reported_comment_id, report_type, severity, description, status, created_at
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reported_recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"))
    reported_comment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("comments.id", ondelete="SET NULL"))
    report_type: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    severity: Mapped[str] = mapped_column(VARCHAR, nullable=False, default="medium")
    description: Mapped[str | None] = mapped_column(VARCHAR)
    status: Mapped[str] = mapped_column(VARCHAR, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── activities ───────────────────────────────────────────────────────
# DDL: id SERIAL, user_id, actor_id, action_type VARCHAR, payload_json JSONB, created_at
class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── conversations ────────────────────────────────────────────────────
# DDL: id SERIAL, participant_ids INTEGER[], last_message_at, created_at
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── messages ─────────────────────────────────────────────────────────
# DDL: id SERIAL, conversation_id FK, sender_id FK, content TEXT NOT NULL, read_at, created_at
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── trusted_reviewers ────────────────────────────────────────────────
# DDL: user_id PK, assigned_by FK, permissions JSONB, revoked_at, created_at
class TrustedReviewer(Base):
    __tablename__ = "trusted_reviewers"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    assigned_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{"can_review": true}')
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── social_challenges ────────────────────────────────────────────────
# DDL: id SERIAL, title VARCHAR, description VARCHAR, challenge_type VARCHAR,
#      start_date DATE, end_date DATE, created_by FK, created_at
class SocialChallenge(Base):
    __tablename__ = "social_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    description: Mapped[str | None] = mapped_column(VARCHAR)
    challenge_type: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── live_rooms ───────────────────────────────────────────────────────
# DDL: id SERIAL, creator_id FK, recipe_id FK, room_type VARCHAR, status VARCHAR, created_at
class LiveRoom(Base):
    __tablename__ = "live_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"))
    room_type: Mapped[str] = mapped_column(VARCHAR, nullable=False, default="personal")
    status: Mapped[str] = mapped_column(VARCHAR, nullable=False, default="scheduled")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── live_participants ────────────────────────────────────────────────
# DDL: id SERIAL PK, room_id FK, user_id FK, role VARCHAR, joined_at, left_at
class LiveParticipant(Base):
    __tablename__ = "live_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("live_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR, nullable=False, default="viewer")
    joined_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


# ── live_room_templates ──────────────────────────────────────────────
# DDL: id SERIAL, name VARCHAR UNIQUE, default_hashtags JSONB, created_at
class LiveRoomTemplate(Base):
    __tablename__ = "live_room_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR, nullable=False, unique=True)
    default_hashtags: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── group_boards ─────────────────────────────────────────────────────
# DDL: id SERIAL, user_id FK, board_name VARCHAR, compact_json JSONB, created_at
# compact_json schema: {"tonight": [...], "this_week": [...], "later": [...]}
# Each slot holds recipe dicts with recipe_id/title/slug for zero-join reads.
class GroupBoard(Base):
    __tablename__ = "group_boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    board_name: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    compact_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── stories ──────────────────────────────────────────────────────────
# DDL: id SERIAL, user_id FK, b2_object_key, story_type, emotion_preset,
#      challenge_id FK, challenge_type, time_preference, file_size_bytes,
#      status, expires_at, created_at
class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    b2_object_key: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    story_type: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    emotion_preset: Mapped[str | None] = mapped_column(VARCHAR)
    challenge_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("social_challenges.id", ondelete="SET NULL"))
    challenge_type: Mapped[str | None] = mapped_column(VARCHAR)
    time_preference: Mapped[str | None] = mapped_column(VARCHAR)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(VARCHAR, nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


# ── story_recipe_links ───────────────────────────────────────────────
# DDL: story_id, recipe_id (composite PK), display_order
class StoryRecipeLink(Base):
    __tablename__ = "story_recipe_links"

    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ── potluck_social_events ────────────────────────────────────────────
# DDL: id SERIAL, session_id, event_type, actor_id FK, payload_json JSONB, created_at
class PotluckSocialEvent(Base):
    __tablename__ = "potluck_social_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    event_type: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'{}'::jsonb")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
