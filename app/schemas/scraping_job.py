from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator

from app.models.scraping_job import JobStatus, ScraperEngine


class ScrapingJobCreate(BaseModel):
    name: str
    target_url: str
    engine: ScraperEngine = ScraperEngine.PLAYWRIGHT
    css_selector: str | None = None
    xpath_selector: str | None = None
    max_pages: int = 1
    delay_seconds: int = 2
    cron_expression: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("max_pages")
    @classmethod
    def max_pages_valid(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("max_pages must be between 1 and 500")
        return v

    @field_validator("delay_seconds")
    @classmethod
    def delay_valid(cls, v: int) -> int:
        if v < 0 or v > 60:
            raise ValueError("delay_seconds must be between 0 and 60")
        return v


class ScrapingJobUpdate(BaseModel):
    name: str | None = None
    css_selector: str | None = None
    xpath_selector: str | None = None
    max_pages: int | None = None
    delay_seconds: int | None = None
    cron_expression: str | None = None
    engine: ScraperEngine | None = None


class ScrapingJobResponse(BaseModel):
    id: int
    name: str
    target_url: str
    status: JobStatus
    engine: ScraperEngine
    css_selector: str | None
    xpath_selector: str | None
    max_pages: int
    delay_seconds: int
    cron_expression: str | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScrapingJobSummary(BaseModel):
    id: int
    name: str
    target_url: str
    status: JobStatus
    engine: ScraperEngine
    max_pages: int
    cron_expression: str | None
    last_run_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedJobs(BaseModel):
    items: list[ScrapingJobSummary]
    total: int
    page: int
    page_size: int
    pages: int
