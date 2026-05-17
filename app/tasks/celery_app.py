from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "scrapflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scraping_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    # Retry policy for transient failures
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Beat schedule: poll for scheduled jobs every minute
celery_app.conf.beat_schedule = {
    "dispatch-scheduled-jobs": {
        "task": "app.tasks.scraping_tasks.dispatch_scheduled_jobs",
        "schedule": crontab(minute="*"),  # every minute
        "options": {"queue": "beat"},
    },
    "cleanup-old-sessions": {
        "task": "app.tasks.scraping_tasks.cleanup_old_sessions",
        "schedule": crontab(hour=3, minute=0),  # daily at 3am UTC
        "options": {"queue": "beat"},
    },
}
