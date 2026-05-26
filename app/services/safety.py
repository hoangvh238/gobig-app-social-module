import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.models.social import Block, Mute

log = logging.getLogger(__name__)

_SAFETY_BUFFER_KEY = "safety:event_buffer"


async def is_blocked(a: int, b: int, db: AsyncSession) -> bool:
    """True if a blocks b, or b blocks a (bidirectional enforcement)."""
    result = await db.execute(
        select(Block.blocker_id).where(
            or_(
                and_(Block.blocker_id == a, Block.blocked_id == b),
                and_(Block.blocker_id == b, Block.blocked_id == a),
            )
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def is_muted(a: int, b: int, db: AsyncSession) -> bool:
    """True if a muted b (unidirectional)."""
    result = await db.execute(
        select(Mute.muter_id).where(
            and_(Mute.muter_id == a, Mute.muted_id == b)
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_blocked_ids(user_id: int, db: AsyncSession) -> set[int]:
    """Return all user IDs that share a block relationship with user_id (either direction)."""
    result = await db.execute(
        select(Block.blocked_id).where(Block.blocker_id == user_id)
        .union(select(Block.blocker_id).where(Block.blocked_id == user_id))
    )
    return {row[0] for row in result.fetchall()}


async def get_muted_ids(user_id: int, db: AsyncSession) -> set[int]:
    """Return all user IDs muted by user_id."""
    result = await db.execute(
        select(Mute.muted_id).where(Mute.muter_id == user_id)
    )
    return {row[0] for row in result.fetchall()}


async def queue_safety_event(event_type: str, payload: dict) -> None:
    """
    Stage a safety event in Redis for batch delivery to Tuan's stream.
    Non-fatal: DB record is already persisted before this is called.
    """
    try:
        from app.redis_client import redis_pool
        entry = json.dumps({"event_type": event_type, **payload})
        await redis_pool.rpush(_SAFETY_BUFFER_KEY, entry)
    except Exception:
        log.warning("safety_event_queue_failed", extra={"event_type": event_type})
