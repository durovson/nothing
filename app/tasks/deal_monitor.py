from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import monotonic

from app.config import Settings
from app.services.channels import ChannelDealService
from app.services.deals import DealService
from app.services.financial_processor import FinancialOperationProcessor
from app.services.lifecycle import DealLifecycleService
from app.services.payouts import PayoutService
from app.services.refunds import RefundService
from app.services.usdt_indexer import UsdtDepositIndexer
from app.services.ton_indexer import TonDepositIndexer
from app.services.system_mode import SystemModeService

logger = logging.getLogger(__name__)


class DealMonitor:
    """Owns isolated background loops and exposes per-worker health."""

    def __init__(
        self,
        settings: Settings,
        deals: DealService,
        lifecycle: DealLifecycleService,
        refunds: RefundService,
        payouts: PayoutService,
        channels: ChannelDealService,
        ton_indexer: TonDepositIndexer,
        usdt_indexer: UsdtDepositIndexer,
        collection_processor: FinancialOperationProcessor,
        refund_processor: FinancialOperationProcessor,
        payout_processor: FinancialOperationProcessor,
        referral_processor: FinancialOperationProcessor,
        unmatched_refund_processor: FinancialOperationProcessor,
        system_mode: SystemModeService,
    ):
        self._settings = settings
        self._deals = deals
        self._lifecycle = lifecycle
        self._refunds = refunds
        self._payouts = payouts
        self._channels = channels
        self._ton_indexer = ton_indexer
        self._usdt_indexer = usdt_indexer
        self._processors = {
            "collection_processor": collection_processor,
            "refund_processor": refund_processor,
            "payout_processor": payout_processor,
            "referral_processor": referral_processor,
            "unmatched_refund_processor": unmatched_refund_processor,
        }
        self._system_mode = system_mode
        self._stop_event = asyncio.Event()
        self._tasks: set[asyncio.Task[None]] = set()
        self._last_success: dict[str, float] = {}

    @property
    def is_running(self) -> bool:
        return bool(self._tasks) and all(not task.done() for task in self._tasks)

    @property
    def worker_health(self) -> dict[str, bool]:
        maximum_age = max(self._settings.DEAL_POLL_INTERVAL_SECONDS * 3, 60)
        now = monotonic()
        task_health = {
            task.get_name(): (
                not task.done()
                and now - self._last_success.get(task.get_name(), 0.0) <= maximum_age
            )
            for task in self._tasks
            if task.get_name() != "retention-archive"
        }
        task_health.update(
            {name: processor.health.healthy for name, processor in self._processors.items()}
        )
        return task_health

    async def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._tasks = {
            asyncio.create_task(self._ton_indexer_loop(), name="ton-deposit-indexer"),
            asyncio.create_task(self._usdt_indexer_loop(), name="usdt-deposit-indexer"),
            asyncio.create_task(self._lifecycle_loop(), name="deal-lifecycle"),
            asyncio.create_task(self._refund_planner_loop(), name="refund-planner"),
            asyncio.create_task(self._payout_planner_loop(), name="payout-planner"),
            asyncio.create_task(self._retention_loop(), name="retention-archive"),
            asyncio.create_task(self._system_mode_loop(), name="system-mode-monitor"),
        }
        self._tasks.update(
            asyncio.create_task(
                self._processor_loop(name, processor), name=name
            )
            for name, processor in self._processors.items()
        )
        started_at = monotonic()
        self._last_success.update({task.get_name(): started_at for task in self._tasks})

    async def stop(self) -> None:
        self._stop_event.set()
        for processor in self._processors.values():
            processor.health.running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _ton_indexer_loop(self) -> None:
        await self._repeat("TON deposit indexer", self._ton_indexer.run_once)

    async def _usdt_indexer_loop(self) -> None:
        await self._repeat("USDT deposit indexer", self._usdt_indexer.run_once)

    async def _refund_planner_loop(self) -> None:
        await self._repeat("Refund planner", self._refunds.process_requested)

    async def _payout_planner_loop(self) -> None:
        await self._repeat("Payout planner", self._payouts.process_releases)

    async def _processor_loop(
        self, name: str, processor: FinancialOperationProcessor
    ) -> None:
        while not self._stop_event.is_set():
            try:
                await processor.run_once()
                self._last_success[name] = monotonic()
            except Exception:
                logger.exception("%s iteration failed", name)
            await self._wait(self._settings.DEAL_POLL_INTERVAL_SECONDS)

    async def _lifecycle_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._channels.process_pending()
            except Exception:
                logger.exception("Channel access reconciliation iteration failed")
            try:
                await self._lifecycle.process_deadlines()
                self._last_success["deal-lifecycle"] = monotonic()
            except Exception:
                logger.exception("Deal deadline iteration failed")
            await self._wait(self._settings.DEAL_POLL_INTERVAL_SECONDS)

    async def _retention_loop(self) -> None:
        await self._repeat(
            "Retention archive",
            self._deals.cleanup_retention,
            self._settings.RETENTION_CLEANUP_INTERVAL_SECONDS,
        )

    async def _system_mode_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                other_workers = {
                    name: healthy
                    for name, healthy in self.worker_health.items()
                    if name != "system-mode-monitor"
                }
                await self._system_mode.reconcile_automatic(all(other_workers.values()))
                self._last_success["system-mode-monitor"] = monotonic()
            except Exception:
                logger.exception("System mode reconciliation failed")
            await self._wait(self._settings.DEAL_POLL_INTERVAL_SECONDS)

    async def _repeat(
        self,
        name: str,
        callback: Callable[[], Awaitable[object]],
        interval: int | None = None,
    ) -> None:
        while not self._stop_event.is_set():
            try:
                await callback()
                task = asyncio.current_task()
                if task is not None:
                    self._last_success[task.get_name()] = monotonic()
            except Exception:
                logger.exception("%s iteration failed", name)
            await self._wait(interval or self._settings.DEAL_POLL_INTERVAL_SECONDS)

    async def _wait(self, timeout: int) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
        except TimeoutError:
            pass
