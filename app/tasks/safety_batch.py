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


@celery_app.task(name="tasks.flush_safety_events")
def flush_safety_events() -> None:
    import redis as _redis
    from app.config import settings

    r = _redis.from_url(settings.redis_url, decode_responses=True)
    """
    # FIX: Sử dụng Redis Lock để đảm bảo chỉ có 1 worker chạy task này
    lock = r.lock("lock:flush_safety_events", timeout=30)
    """
    events = r.lrange(_BUFFER_KEY, 0, _DRAIN_BATCH - 1)
    if not events:
        return

    # FIX: Xử lý xong mới Trim (vì lỡ crash mà chứ sử lý thì mất record luôn thì sao)
    r.ltrim(_BUFFER_KEY, len(events), -1)

    pipe = r.pipeline(transaction=False)
    for raw in events:
        try:
            entry = json.loads(raw)
            pipe.xadd(_STREAM_KEY, {k: str(v) for k, v in entry.items()})
        except (json.JSONDecodeError, Exception) as exc:
            log.warning("safety_batch_bad_entry", extra={"error": str(exc)})

    pipe.execute()
    log.info("safety_batch_flushed", extra={"count": len(events)})
