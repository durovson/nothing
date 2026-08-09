from __future__ import annotations

import asyncio
from time import monotonic

from app.core.types import TonGatewayProtocol


class HealthService:
    """Cached TON API availability probe used by service health endpoints."""

    def __init__(
        self,
        ton: TonGatewayProtocol,
        cache_seconds: int = 30,
    ):
        self._ton = ton
        self._cache_seconds = cache_seconds
        self._lock = asyncio.Lock()
        self._cached_at = 0.0
        self._cached: dict[str, object] | None = None

    async def check(self) -> dict[str, object]:
        now = monotonic()
        if self._cached is not None and now - self._cached_at < self._cache_seconds:
            return self._cached
        async with self._lock:
            now = monotonic()
            if self._cached is not None and now - self._cached_at < self._cache_seconds:
                return self._cached
            tonapi = await self._probe(self._ton.get_guarant_balance_atomic)
            checks: dict[str, bool] = {"tonapi": tonapi}
            self._cached = {
                "status": "ok" if tonapi else "degraded",
                "checks": checks,
            }
            self._cached_at = now
            return self._cached

    @staticmethod
    async def _probe(callback) -> bool:
        try:
            await asyncio.wait_for(callback(), timeout=10)
            return True
        except Exception:
            return False
