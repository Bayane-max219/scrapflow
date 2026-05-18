import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy_pool import ProxyPool

logger = logging.getLogger(__name__)

# Minimum success rate before a proxy is auto-disabled
_MIN_SUCCESS_RATE = 0.25
# Cooldown seconds between reusing the same proxy
_PROXY_COOLDOWN = 30
# Timeout for proxy health check
_HEALTH_CHECK_TIMEOUT = 8


class ProxyRotationService:
    """
    Selects the best proxy from the pool using weighted random selection
    weighted by success_rate, with cooldown enforcement and auto-disable
    for consistently failing proxies.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_best_proxy(self) -> ProxyPool | None:
        """
        Returns the best available proxy using weighted selection.
        Respects per-proxy cooldowns and skips unhealthy ones.
        """
        now = datetime.now(timezone.utc)
        result = await self._db.execute(
            select(ProxyPool)
            .where(
                ProxyPool.is_active == True,
                ProxyPool.success_rate >= _MIN_SUCCESS_RATE,
            )
            .order_by(ProxyPool.success_rate.desc(), ProxyPool.response_time_ms.asc())
        )
        candidates = result.scalars().all()

        if not candidates:
            logger.warning("No active proxies available in pool")
            return None

        # Filter by cooldown
        cooled_candidates = [
            p for p in candidates
            if p.last_used_at is None
            or (now - p.last_used_at).total_seconds() >= _PROXY_COOLDOWN
        ]

        if not cooled_candidates:
            # All proxies are on cooldown — pick the least recently used
            candidates_sorted = sorted(candidates, key=lambda p: p.last_used_at or datetime.min.replace(tzinfo=timezone.utc))
            return candidates_sorted[0]

        # Weighted random selection by success_rate
        total_weight = sum(p.success_rate for p in cooled_candidates)
        pick = random.uniform(0, total_weight)
        cumulative = 0.0
        for proxy in cooled_candidates:
            cumulative += proxy.success_rate
            if pick <= cumulative:
                return proxy

        return cooled_candidates[0]

    async def mark_success(self, proxy_id: int, response_time_ms: int) -> None:
        """Updates success_rate (EMA) and response_time_ms after a successful request."""
        result = await self._db.execute(select(ProxyPool).where(ProxyPool.id == proxy_id))
        proxy = result.scalar_one_or_none()
        if proxy is None:
            return

        # Exponential Moving Average for success_rate (α=0.1)
        proxy.success_rate = min(1.0, proxy.success_rate * 0.9 + 0.1)
        proxy.response_time_ms = int(proxy.response_time_ms * 0.8 + response_time_ms * 0.2)
        proxy.last_used_at = datetime.now(timezone.utc)
        await self._db.commit()

    async def mark_failure(self, proxy_id: int) -> None:
        """Penalizes success_rate after a failure; auto-disables if rate < threshold."""
        result = await self._db.execute(select(ProxyPool).where(ProxyPool.id == proxy_id))
        proxy = result.scalar_one_or_none()
        if proxy is None:
            return

        # EMA penalty
        proxy.success_rate = max(0.0, proxy.success_rate * 0.9)
        proxy.last_used_at = datetime.now(timezone.utc)

        if proxy.success_rate < _MIN_SUCCESS_RATE:
            proxy.is_active = False
            logger.warning("Proxy %s:%d auto-disabled (success_rate=%.2f)", proxy.host, proxy.port, proxy.success_rate)

        await self._db.commit()

    async def health_check(self, proxy: ProxyPool, test_url: str = "https://httpbin.org/ip") -> bool:
        """
        Validates proxy connectivity via HEAD request.
        Updates success_rate and response_time_ms accordingly.
        """
        proxy_url = proxy.get_url()
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=_HEALTH_CHECK_TIMEOUT,
                follow_redirects=True,
            ) as client:
                resp = await client.get(test_url)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code < 400:
                    await self.mark_success(proxy.id, elapsed_ms)
                    logger.debug("Proxy %s:%d healthy (%dms)", proxy.host, proxy.port, elapsed_ms)
                    return True
                else:
                    await self.mark_failure(proxy.id)
                    return False

        except Exception as exc:
            logger.warning("Proxy %s:%d health check failed: %s", proxy.host, proxy.port, exc)
            await self.mark_failure(proxy.id)
            return False

    async def health_check_all(self) -> dict[str, Any]:
        """Runs health checks on all active proxies in parallel."""
        result = await self._db.execute(select(ProxyPool).where(ProxyPool.is_active == True))
        proxies = result.scalars().all()

        tasks = [self.health_check(p) for p in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy = sum(1 for r in results if r is True)
        failed = len(proxies) - healthy

        logger.info("Proxy health check: %d healthy, %d failed / %d total", healthy, failed, len(proxies))
        return {"total": len(proxies), "healthy": healthy, "failed": failed}
