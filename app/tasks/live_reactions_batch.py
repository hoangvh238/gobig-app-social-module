"""
Celery beat task: drain live reaction buffer → live_reaction_events table.
Runs every 30 seconds; never writes per-reaction to DB on the hot path.
"""
import asyncio
import json
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)

_BUFFER_KEY = "live:reaction_buffer"
_DRAIN_BATCH = 1000


async def _insert_reactions(rows: list[dict]) -> None:
    from sqlalchemy import text
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO live_reaction_events (room_id, user_id, reaction_type) "
                "VALUES (:room_id, :user_id, :reaction_type)"
            ),
            rows,
        )
        await session.commit()


@celery_app.task(name="tasks.flush_live_reactions")
def flush_live_reactions() -> None:
    import redis as _redis
    from app.config import settings

    r = _redis.from_url(settings.redis_url, decode_responses=True)

    raw_events = r.lrange(_BUFFER_KEY, 0, _DRAIN_BATCH - 1)
    if not raw_events:
        return

    r.ltrim(_BUFFER_KEY, len(raw_events), -1)

    rows = []
    for raw in raw_events:
        try:
            entry = json.loads(raw)
            rows.append({
                "room_id": int(entry["room_id"]),
                "user_id": int(entry["user_id"]),
                "reaction_type": str(entry["reaction_type"]),
            })
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            log.warning("live_reaction_bad_entry", extra={"error": str(exc)})

    if not rows:
        return

    asyncio.run(_insert_reactions(rows))
    log.info("live_reactions_flushed", extra={"count": len(rows)})
