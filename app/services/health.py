from __future__ import annotations

import asyncio
from time import monotonic

from aiogram import Bot

from app.core.types import TonGatewayProtocol
from app.database import SupabaseDatabase
from app.tasks.deal_monitor import DealMonitor


class HealthService:
    """Cached live probes for infrastructure and background workers."""

    def __init__(
        self,
        database: SupabaseDatabase,
        ton: TonGatewayProtocol,
        bot: Bot,
        monitor: DealMonitor,
        cache_seconds: int = 30,
    ):
        self._database = database
        self._ton = ton
        self._bot = bot
        self._monitor = monitor
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
            supabase, tonapi, telegram = await asyncio.gather(
                self._probe(self._database.ping),
                self._probe(self._ton.get_guarant_balance_atomic),
                self._probe(self._bot.get_me),
            )
            workers = self._monitor.worker_health
            checks: dict[str, bool] = {
                "supabase": supabase,
                "tonapi": tonapi,
                "telegram": telegram,
                **{f"worker:{name}": healthy for name, healthy in workers.items()},
            }
            self._cached = {
                "status": "ok" if checks and all(checks.values()) else "degraded",
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
