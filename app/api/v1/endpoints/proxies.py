from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.proxy_pool import ProxyPool
from app.schemas.proxy_pool import ProxyCreate, ProxyResponse, ProxyUpdate
from app.services.proxy_rotation_service import ProxyRotationService

router = APIRouter()


@router.post("/health-check", summary="Run health check on all active proxies")
async def health_check_all(db: AsyncSession = Depends(get_db)):
    """Tests all active proxies and updates their success_rate + response_time_ms."""
    service = ProxyRotationService(db)
    return await service.health_check_all()


@router.post("/{proxy_id}/health-check", summary="Run health check on a single proxy")
async def health_check_one(proxy_id: int, db: AsyncSession = Depends(get_db)):
    """Tests a single proxy and updates its metrics."""
    result = await db.execute(select(ProxyPool).where(ProxyPool.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if proxy is None:
        raise HTTPException(status_code=404, detail="Proxy not found")

    service = ProxyRotationService(db)
    healthy = await service.health_check(proxy)
    return {"proxy_id": proxy_id, "healthy": healthy}


@router.get("", response_model=list[ProxyResponse])
async def list_proxies(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(ProxyPool)
    if active_only:
        query = query.where(ProxyPool.is_active == True)
    query = query.order_by(ProxyPool.success_rate.desc(), ProxyPool.response_time_ms.asc())
    result = await db.execute(query)
    return [ProxyResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=ProxyResponse, status_code=status.HTTP_201_CREATED)
async def add_proxy(payload: ProxyCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(ProxyPool).where(ProxyPool.host == payload.host, ProxyPool.port == payload.port)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Proxy already exists")

    proxy = ProxyPool(
        host=payload.host,
        port=payload.port,
        protocol=payload.protocol,
        username=payload.username,
        password=payload.password,
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return ProxyResponse.model_validate(proxy)


@router.patch("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(proxy_id: int, payload: ProxyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProxyPool).where(ProxyPool.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if proxy is None:
        raise HTTPException(status_code=404, detail="Proxy not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(proxy, field, value)

    await db.commit()
    await db.refresh(proxy)
    return ProxyResponse.model_validate(proxy)


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy(proxy_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProxyPool).where(ProxyPool.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if proxy is None:
        raise HTTPException(status_code=404, detail="Proxy not found")

    await db.delete(proxy)
    await db.commit()


@router.get("/best", response_model=ProxyResponse)
async def get_best_proxy(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProxyPool)
        .where(ProxyPool.is_active == True)
        .order_by(ProxyPool.success_rate.desc(), ProxyPool.response_time_ms.asc())
        .limit(1)
    )
    proxy = result.scalar_one_or_none()
    if proxy is None:
        raise HTTPException(status_code=404, detail="No active proxy available")
    return ProxyResponse.model_validate(proxy)
