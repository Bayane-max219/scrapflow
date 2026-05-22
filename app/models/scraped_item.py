import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ItemStatus(str, enum.Enum):
    RAW = "raw"
    VALIDATED = "validated"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class ScrapedItem(Base):
    __tablename__ = "scraped_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("scraping_jobs.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("scraping_sessions.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus, values_callable=lambda x: [e.value for e in x]), default=ItemStatus.RAW, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["ScrapingJob"] = relationship(back_populates="items")
    session: Mapped["ScrapingSession | None"] = relationship(back_populates="items")
