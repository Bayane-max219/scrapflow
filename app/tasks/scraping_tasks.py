import asyncio
import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.scraping_job import JobStatus, ScrapingJob
from app.models.scraping_session import ScrapingSession
from app.models.scraped_item import ItemStatus, ScrapedItem
from app.services.scraper_dispatcher import ScraperDispatcher
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sync SQLAlchemy engine for Celery tasks (Celery workers are synchronous)
_sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SyncSessionLocal = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)


@celery_app.task(
    bind=True,
    name="app.tasks.scraping_tasks.run_scraping_job",
    max_retries=3,
    default_retry_delay=60,
    queue="scraping",
)
def run_scraping_job(self, job_id: int) -> dict:
    """
    Main scraping task. Creates a session, runs the dispatcher, saves items.
    Retries up to 3 times on transient errors (network, bot detection).
    """
    logger.info("Starting scraping task for job_id=%d (attempt %d)", job_id, self.request.retries + 1)

    with SyncSessionLocal() as db:
        job = db.get(ScrapingJob, job_id)
        if not job:
            logger.error("Job %d not found", job_id)
            return {"error": f"Job {job_id} not found"}

        if job.status == JobStatus.PAUSED:
            logger.info("Job %d is paused, skipping", job_id)
            return {"status": "skipped", "reason": "paused"}

        # Create session record
        session = ScrapingSession(
            job_id=job_id,
            celery_task_id=self.request.id,
            engine_used=job.engine.value,
        )
        db.add(session)

        # Mark job as running
        job.status = JobStatus.RUNNING
        job.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

        try:
            items, engine_used = asyncio.run(
                ScraperDispatcher().run(
                    engine=job.engine,
                    url=job.target_url,
                    css_selector=job.css_selector,
                    xpath_selector=job.xpath_selector,
                    max_pages=job.max_pages,
                    delay_seconds=job.delay_seconds,
                )
            )

            session.engine_used = engine_used
            session.items_found = len(items)

            # Dedup: collect existing content hashes for this job
            existing_hashes = {
                row[0]
                for row in db.execute(
                    select(ScrapedItem.content_hash).where(
                        ScrapedItem.job_id == job_id,
                        ScrapedItem.content_hash.isnot(None),
                    )
                )
            }

            saved = 0
            duplicated = 0
            for raw in items:
                h = raw.get("content_hash")
                if h and h in existing_hashes:
                    duplicated += 1
                    continue

                item = ScrapedItem(
                    job_id=job_id,
                    session_id=session.id,
                    url=raw.get("url", job.target_url),
                    data=raw,
                    status=ItemStatus.RAW,
                    content_hash=h,
                )
                db.add(item)
                if h:
                    existing_hashes.add(h)
                saved += 1

            session.items_saved = saved
            session.items_duplicated = duplicated
            session.finished_at = datetime.now(timezone.utc)
            job.status = JobStatus.COMPLETED
            db.commit()

            logger.info(
                "Job %d completed: %d found, %d saved, %d duplicates (engine=%s)",
                job_id, len(items), saved, duplicated, engine_used,
            )
            return {
                "job_id": job_id,
                "session_id": session.id,
                "engine_used": engine_used,
                "items_found": len(items),
                "items_saved": saved,
                "items_duplicated": duplicated,
            }

        except Exception as exc:
            logger.error("Job %d failed: %s", job_id, exc)
            session.error_message = str(exc)[:2048]
            session.finished_at = datetime.now(timezone.utc)
            job.status = JobStatus.FAILED
            db.commit()

            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error("Job %d exceeded max retries", job_id)
                return {"error": str(exc), "job_id": job_id, "retries_exhausted": True}


@celery_app.task(
    name="app.tasks.scraping_tasks.dispatch_scheduled_jobs",
    queue="beat",
)
def dispatch_scheduled_jobs() -> dict:
    """
    Beat task: finds jobs with a cron schedule whose next_run_at is overdue,
    dispatches a run_scraping_job task for each, and updates next_run_at.
    """
    now = datetime.now(timezone.utc)
    dispatched = []

    with SyncSessionLocal() as db:
        due_jobs = db.execute(
            select(ScrapingJob).where(
                ScrapingJob.cron_expression.isnot(None),
                ScrapingJob.next_run_at <= now,
                ScrapingJob.status.in_([JobStatus.PENDING, JobStatus.COMPLETED, JobStatus.FAILED]),
            )
        ).scalars().all()

        for job in due_jobs:
            run_scraping_job.apply_async(args=[job.id], queue="scraping")
            job.next_run_at = _next_run_from_cron(job.cron_expression)
            dispatched.append(job.id)
            logger.info("Dispatched job %d (cron=%s)", job.id, job.cron_expression)

        db.commit()

    logger.info("Beat: dispatched %d scheduled jobs", len(dispatched))
    return {"dispatched": dispatched, "count": len(dispatched)}


@celery_app.task(
    name="app.tasks.scraping_tasks.cleanup_old_sessions",
    queue="beat",
)
def cleanup_old_sessions(days: int = 30) -> dict:
    """
    Daily cleanup: removes sessions and items older than `days` days.
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with SyncSessionLocal() as db:
        old_sessions = db.execute(
            select(ScrapingSession).where(ScrapingSession.started_at < cutoff)
        ).scalars().all()

        count = len(old_sessions)
        for s in old_sessions:
            db.delete(s)

        db.commit()

    logger.info("Cleanup: deleted %d sessions older than %d days", count, days)
    return {"deleted_sessions": count, "cutoff": cutoff.isoformat()}


def _next_run_from_cron(cron_expression: str | None) -> datetime | None:
    """
    Computes the next run datetime from a simple cron expression.
    Uses croniter when available, falls back to +1 hour.
    """
    if not cron_expression:
        return None

    try:
        from croniter import croniter  # pip install croniter
        base = datetime.now(timezone.utc)
        return croniter(cron_expression, base).get_next(datetime)
    except ImportError:
        from datetime import timedelta
        return datetime.now(timezone.utc) + timedelta(hours=1)
