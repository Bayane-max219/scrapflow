import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.scraping_job import JobStatus, ScrapingJob
from app.schemas.scraping_job import (
    PaginatedJobs,
    ScrapingJobCreate,
    ScrapingJobResponse,
    ScrapingJobSummary,
    ScrapingJobUpdate,
)

router = APIRouter()


@router.post("/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def trigger_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Manually dispatch a scraping job to Celery workers."""
    from app.tasks.scraping_tasks import run_scraping_job

    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Job is already running")

    task = run_scraping_job.apply_async(args=[job_id], queue="scraping")
    return {"job_id": job_id, "celery_task_id": task.id, "status": "queued"}


@router.get("", response_model=PaginatedJobs)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: JobStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    query = select(ScrapingJob)
    count_query = select(func.count()).select_from(ScrapingJob)

    if status is not None:
        query = query.where(ScrapingJob.status == status)
        count_query = count_query.where(ScrapingJob.status == status)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.order_by(ScrapingJob.created_at.desc()).offset(offset).limit(page_size))
    jobs = result.scalars().all()

    return PaginatedJobs(
        items=[ScrapingJobSummary.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("", response_model=ScrapingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(payload: ScrapingJobCreate, db: AsyncSession = Depends(get_db)):
    job = ScrapingJob(
        name=payload.name,
        target_url=str(payload.target_url),
        engine=payload.engine,
        css_selector=payload.css_selector,
        xpath_selector=payload.xpath_selector,
        max_pages=payload.max_pages,
        delay_seconds=payload.delay_seconds,
        cron_expression=payload.cron_expression,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return ScrapingJobResponse.model_validate(job)


@router.get("/{job_id}", response_model=ScrapingJobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return ScrapingJobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=ScrapingJobResponse)
async def update_job(job_id: int, payload: ScrapingJobUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Cannot update a running job")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return ScrapingJobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Cannot delete a running job — pause it first")

    await db.delete(job)
    await db.commit()


@router.patch("/{job_id}/pause", response_model=ScrapingJobResponse)
async def pause_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.RUNNING, JobStatus.PENDING):
        raise HTTPException(status_code=409, detail=f"Cannot pause a job with status '{job.status}'")

    job.status = JobStatus.PAUSED
    await db.commit()
    await db.refresh(job)
    return ScrapingJobResponse.model_validate(job)


@router.patch("/{job_id}/resume", response_model=ScrapingJobResponse)
async def resume_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=409, detail="Only paused jobs can be resumed")

    job.status = JobStatus.PENDING
    await db.commit()
    await db.refresh(job)
    return ScrapingJobResponse.model_validate(job)
