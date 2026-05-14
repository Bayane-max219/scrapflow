from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ScrapingSession(Base):
    __tablename__ = "scraping_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("scraping_jobs.id", ondelete="CASCADE"), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    engine_used: Mapped[str] = mapped_column(String(50), nullable=False)
    pages_scraped: Mapped[int] = mapped_column(Integer, default=0)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_saved: Mapped[int] = mapped_column(Integer, default=0)
    items_duplicated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["ScrapingJob"] = relationship(back_populates="sessions")
    items: Mapped[list["ScrapedItem"]] = relationship(back_populates="session")

    @property
    def duration_seconds(self) -> int | None:
        if self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None
