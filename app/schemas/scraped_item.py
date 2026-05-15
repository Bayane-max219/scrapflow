from datetime import datetime
from pydantic import BaseModel

from app.models.scraped_item import ItemStatus


class ScrapedItemResponse(BaseModel):
    id: int
    job_id: int
    session_id: int | None
    url: str
    data: dict
    status: ItemStatus
    content_hash: str | None
    scraped_at: datetime

    model_config = {"from_attributes": True}


class PaginatedItems(BaseModel):
    items: list[ScrapedItemResponse]
    total: int
    page: int
    page_size: int
    pages: int
