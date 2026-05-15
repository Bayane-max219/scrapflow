from datetime import datetime
from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: int
    job_id: int
    celery_task_id: str | None
    engine_used: str
    pages_scraped: int
    items_found: int
    items_saved: int
    items_duplicated: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: int | None

    model_config = {"from_attributes": True}
