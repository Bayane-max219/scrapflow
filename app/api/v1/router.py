from fastapi import APIRouter

from app.api.v1.endpoints import health, items, jobs, proxies

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(proxies.router, prefix="/proxies", tags=["proxies"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
