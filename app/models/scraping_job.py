import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ScraperEngine(str, enum.Enum):
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    HTTPX = "httpx"


class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    engine: Mapped[ScraperEngine] = mapped_column(
        Enum(ScraperEngine), default=ScraperEngine.PLAYWRIGHT, nullable=False
    )
    css_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    xpath_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_pages: Mapped[int] = mapped_column(Integer, default=1)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=2)
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ScrapedItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    sessions: Mapped[list["ScrapingSession"]] = relationship(back_populates="job", cascade="all, delete-orphan")
