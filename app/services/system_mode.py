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
    """TON-only circuit breaker with administrator-controlled manual modes."""

    _CACHE_TTL_SECONDS = 30
    _PERSIST_RETRY_SECONDS = 60

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
        self._cache_lock = asyncio.Lock()
        self._failure_started_at: datetime | None = None
        self._local_read_only = False
        self._persist_retry_at = datetime.min.replace(tzinfo=UTC)

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
            async with self._cache_lock:
                now = datetime.now(UTC)
                if force or self._cached is None or now >= self._cache_until:
                    self._cached = await self._repository.get_mode()
                    self._cache_until = now + timedelta(
                        seconds=self._CACHE_TTL_SECONDS
                    )
        return self._cached

    async def set_manual(
        self, mode: SystemMode, reason: str, actor_id: int
    ) -> SystemSetting:
        self._local_read_only = False
        self._persist_retry_at = datetime.min.replace(tzinfo=UTC)
        self._cached = await self._repository.set_mode(
            mode, reason, updated_by=actor_id, automatic=False
        )
        self._cache_until = datetime.now(UTC) + timedelta(
            seconds=self._CACHE_TTL_SECONDS
        )
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

    async def reconcile_automatic(self) -> None:
        """Enter automatic READ_ONLY only after a sustained TON provider outage."""
        ton_healthy = await self._probe(self._ton.get_guarant_balance_atomic)
        now = datetime.now(UTC)
        if ton_healthy:
            self._failure_started_at = None
            if self._local_read_only:
                self._local_read_only = False
            current = self._cached
            if (
                current is not None
                and current.mode is SystemMode.READ_ONLY
                and current.automatic
            ):
                if now < self._persist_retry_at:
                    return
                try:
                    self._cached = await self._repository.set_mode(
                        SystemMode.NORMAL,
                        "TON provider recovered",
                        updated_by=None,
                        automatic=True,
                    )
                    self._cache_until = now + timedelta(
                        seconds=self._CACHE_TTL_SECONDS
                    )
                    self._persist_retry_at = datetime.min.replace(tzinfo=UTC)
                except Exception:
                    self._persist_retry_at = now + timedelta(
                        seconds=self._PERSIST_RETRY_SECONDS
                    )
                    logger.warning(
                        "TON recovered, but automatic NORMAL could not be persisted; retrying later"
                    )
            return

        self._failure_started_at = self._failure_started_at or now
        elapsed = (now - self._failure_started_at).total_seconds()
        if elapsed < self._settings.READ_ONLY_FAILURE_THRESHOLD_SECONDS:
            return
        if self._local_read_only:
            return
        if self._cached is not None and self._cached.mode is not SystemMode.NORMAL:
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
                    "TON provider unavailable beyond the configured threshold",
                    updated_by=None,
                    automatic=True,
                )
                self._cache_until = now + timedelta(
                    seconds=self._CACHE_TTL_SECONDS
                )
                self._local_read_only = False
        except Exception:
            logger.warning(
                "TON is unavailable and READ_ONLY could not be persisted; local circuit breaker is active"
            )

    @staticmethod
    async def _probe(callback) -> bool:
        try:
            await asyncio.wait_for(callback(), timeout=10)
            return True
        except Exception:
            return False
