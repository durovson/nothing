from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.services.deals import DealService
from app.services.payments import PaymentService
from app.services.payouts import PayoutService

logger = logging.getLogger(__name__)


class DealMonitor:
    """Owns independent payment, payout and retention background loops."""

    def __init__(
        self,
        settings: Settings,
        deals: DealService,
        payments: PaymentService,
        payouts: PayoutService,
    ):
        self._settings = settings
        self._deals = deals
        self._payments = payments
        self._payouts = payouts
        self._stop_event = asyncio.Event()
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def is_running(self) -> bool:
        return bool(self._tasks) and all(not task.done() for task in self._tasks)

    async def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._tasks = {
            asyncio.create_task(self._payment_loop(), name="payment-monitor"),
            asyncio.create_task(self._payout_loop(), name="payout-reconciler"),
            asyncio.create_task(self._retention_loop(), name="retention-cleanup"),
        }

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _payment_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._payments.process_pending()
            except Exception:
                logger.exception("Payment monitor iteration failed")
            await self._wait(self._settings.DEAL_POLL_INTERVAL_SECONDS)

    async def _payout_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._payouts.reconcile_open()
            except Exception:
                logger.exception("Payout reconciliation iteration failed")
            await self._wait(self._settings.DEAL_POLL_INTERVAL_SECONDS)

    async def _retention_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._deals.cleanup_retention()
            except Exception:
                logger.exception("Retention cleanup iteration failed")
            await self._wait(self._settings.RETENTION_CLEANUP_INTERVAL_SECONDS)

    async def _wait(self, timeout: int) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
        except TimeoutError:
            pass

