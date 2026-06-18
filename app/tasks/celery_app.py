"""
Celery app configuration — uses external broker.
Worker runs as a separate process alongside the FastAPI app.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "gobig_social",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="social",
    beat_schedule={
        "flush-safety-events-every-60s": {
            "task": "tasks.flush_safety_events",
            "schedule": 60.0,
        },
        "flush-live-reactions-every-30s": {
            "task": "tasks.flush_live_reactions",
            "schedule": 30.0,
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
