from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import FinancialOperationFlow, SystemMode
from app.core.exceptions import ServiceUnavailableError
from app.database import SupabaseDatabase
from app.models.entities import SystemSetting
from app.repositories.system import SystemSettingsRepository
from app.ton.client import TonEscrowClient

logger = logging.getLogger(__name__)


class SystemModeService:
    """Hybrid circuit breaker: automatic READ_ONLY, manual EMERGENCY."""

    def __init__(
        self,
        settings: Settings,
        repository: SystemSettingsRepository,
        database: SupabaseDatabase,
        ton: TonEscrowClient,
    ):
        self._settings = settings
        self._repository = repository
        self._database = database
        self._ton = ton
        self._cached: SystemSetting | None = None
        self._cache_until = datetime.min.replace(tzinfo=UTC)
        self._failure_started_at: datetime | None = None
        self._local_read_only = False

    async def current(self, *, force: bool = False) -> SystemSetting:
        if self._local_read_only:
            return SystemSetting(
                key="system_mode",
                value=SystemMode.READ_ONLY.value,
                reason="Infrastructure health check failed continuously",
                automatic=True,
            )
        now = datetime.now(UTC)
        if force or self._cached is None or now >= self._cache_until:
            self._cached = await self._repository.get_mode()
            self._cache_until = now + timedelta(seconds=5)
        return self._cached

    async def set_manual(
        self, mode: SystemMode, reason: str, actor_id: int
    ) -> SystemSetting:
        self._local_read_only = False
        self._cached = await self._repository.set_mode(
            mode, reason, updated_by=actor_id, automatic=False
        )
        self._cache_until = datetime.now(UTC) + timedelta(seconds=5)
        return self._cached

    async def ensure_new_business_allowed(self) -> None:
        setting = await self.current()
        if setting.mode is not SystemMode.NORMAL:
            raise ServiceUnavailableError(
                "Сервис временно работает в режиме обслуживания. Новые сделки и платежи недоступны."
            )

    async def accepts_deposits(self) -> bool:
        # READ_ONLY blocks creation/join/payment UI, but transfers already sent
        # on-chain cannot be stopped. Keep indexing and collection/recovery alive
        # so an infrastructure incident cannot strand those funds unnoticed.
        return (await self.current()).mode is not SystemMode.EMERGENCY

    async def allows_flow(self, flow: FinancialOperationFlow) -> bool:
        mode = (await self.current()).mode
        if mode is not SystemMode.EMERGENCY:
            return True
        return flow in {FinancialOperationFlow.REFUND, FinancialOperationFlow.UNMATCHED_REFUND}

    async def reconcile_automatic(self, workers_healthy: bool) -> None:
        probes = await asyncio.gather(
            self._probe(self._database.ping),
            self._probe(self._ton.get_guarant_balance_atomic),
        )
        healthy = workers_healthy and all(probes)
        now = datetime.now(UTC)
        if healthy:
            self._failure_started_at = None
            if self._local_read_only:
                self._local_read_only = False
            try:
                current = await self.current(force=True)
                if current.mode is SystemMode.READ_ONLY and current.automatic:
                    self._cached = await self._repository.set_mode(
                        SystemMode.NORMAL,
                        "Infrastructure recovered",
                        updated_by=None,
                        automatic=True,
                    )
            except Exception:
                logger.warning("Could not persist automatic NORMAL mode", exc_info=True)
                return
            return

        self._failure_started_at = self._failure_started_at or now
        elapsed = (now - self._failure_started_at).total_seconds()
        if elapsed < self._settings.READ_ONLY_FAILURE_THRESHOLD_SECONDS:
            return
        self._local_read_only = True
        try:
            current = await self._repository.get_mode()
            if current.mode is SystemMode.EMERGENCY:
                self._cached = current
                self._local_read_only = False
            else:
                self._cached = await self._repository.set_mode(
                    SystemMode.READ_ONLY,
                    "Infrastructure unhealthy for at least 15 minutes",
                    updated_by=None,
                    automatic=True,
                )
                self._local_read_only = False
        except Exception:
            logger.warning(
                "Could not persist READ_ONLY; keeping the local circuit breaker",
                exc_info=True,
            )

    @staticmethod
    async def _probe(callback) -> bool:
        try:
            await asyncio.wait_for(callback(), timeout=10)
            return True
        except Exception:
            return False
