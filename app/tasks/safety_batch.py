"""
Celery beat task: drain safety event buffer → Tuan's Redis Stream.
Runs every 60 seconds; never writes per-action to the stream.
"""
import json
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)

_BUFFER_KEY = "safety:event_buffer"
_STREAM_KEY = "safety:events"
_DRAIN_BATCH = 500
_LOCK_KEY = "lock:flush_safety_events"
_LOCK_TIMEOUT = 30


@celery_app.task(name="tasks.flush_safety_events")
def flush_safety_events() -> None:
    import redis as _redis
    from app.config import settings

    r = _redis.from_url(settings.redis_url, decode_responses=True)

    # Distributed lock prevents concurrent Celery workers from double-draining.
    lock = r.lock(_LOCK_KEY, timeout=_LOCK_TIMEOUT)
    if not lock.acquire(blocking=False):
        return

    try:
        events = r.lrange(_BUFFER_KEY, 0, _DRAIN_BATCH - 1)
        if not events:
            return

        # Write to stream BEFORE trimming the buffer. If the process crashes
        # mid-flight, events remain in the buffer and will be retried next tick.
        pipe = r.pipeline(transaction=False)
        for raw in events:
            try:
                entry = json.loads(raw)
                pipe.xadd(_STREAM_KEY, {k: str(v) for k, v in entry.items()})
            except (json.JSONDecodeError, Exception) as exc:
                log.warning("safety_batch_bad_entry", extra={"error": str(exc)})

        pipe.execute()
        r.ltrim(_BUFFER_KEY, len(events), -1)
        log.info("safety_batch_flushed", extra={"count": len(events)})
    finally:
        try:
            lock.release()
        except Exception:
            pass
