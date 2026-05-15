import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.scraped_item import ItemStatus, ScrapedItem
from app.schemas.scraped_item import PaginatedItems, ScrapedItemResponse

router = APIRouter()


@router.get("", response_model=PaginatedItems)
async def list_items(
    job_id: int | None = Query(None),
    status: ItemStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    query = select(ScrapedItem)
    count_query = select(func.count()).select_from(ScrapedItem)

    if job_id is not None:
        query = query.where(ScrapedItem.job_id == job_id)
        count_query = count_query.where(ScrapedItem.job_id == job_id)

    if status is not None:
        query = query.where(ScrapedItem.status == status)
        count_query = count_query.where(ScrapedItem.status == status)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(ScrapedItem.scraped_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedItems(
        items=[ScrapedItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 1,
    )
