from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import FinancialAttemptStatus, FinancialOperationFlow, TraceStatus
from app.core.types import DealRepositoryProtocol, FinancialOperationRepositoryProtocol, TonGatewayProtocol
from app.models.entities import FinancialOperation, FinancialOperationAttempt
from app.services.balances import FinancialBalanceGuard
from app.services.system_mode import SystemModeService
from app.ton.models import PayoutMessage


@dataclass(slots=True)
class ProcessorHealth:
    running: bool = False
    iterations: int = 0
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None

    @property
    def healthy(self) -> bool:
        if not self.running:
            return False
        if self.last_success_at is None:
            return True
        stale_after = datetime.now(UTC) - timedelta(minutes=5)
        return self.last_success_at >= stale_after


class FinancialOperationProcessor:
    """Executes one ledger leg at a time and never replays an uncertain transfer."""

    def __init__(
        self,
        settings: Settings,
        flow: FinancialOperationFlow,
        operations: FinancialOperationRepositoryProtocol,
        ton: TonGatewayProtocol,
        on_confirmed: Callable[[FinancialOperation], Awaitable[None]] | None = None,
        deals: DealRepositoryProtocol | None = None,
        system_mode: SystemModeService | None = None,
    ):
        self.flow = flow
        self.health = ProcessorHealth()
        self._settings = settings
        self._operations = operations
        self._ton = ton
        self._balances = FinancialBalanceGuard(settings, ton)
        self._on_confirmed = on_confirmed
        self._deals = deals
        self._system_mode = system_mode
        self._logger = logging.getLogger(f"{__name__}.{flow.value}")

    async def run_once(self) -> None:
        self.health.running = True
        try:
            if self._system_mode is not None and not await self._system_mode.allows_flow(self.flow):
                self.health.iterations += 1
                self.health.last_success_at = datetime.now(UTC)
                self.health.last_error = None
                return
            for operation, attempt in await self._operations.list_submitted(self.flow):
                await self._reconcile(operation, attempt)
            operation = await self._operations.claim_due(self.flow)
            if operation is not None:
                await self._prepare_and_submit(operation)
            self.health.iterations += 1
            self.health.last_success_at = datetime.now(UTC)
            self.health.last_error = None
        except Exception as exc:
            self.health.last_error_at = datetime.now(UTC)
            self.health.last_error = str(exc)[:500]
            raise

    async def _prepare_and_submit(self, operation: FinancialOperation) -> None:
        try:
            if operation.flow is FinancialOperationFlow.COLLECTION:
                if operation.deal_id is None or self._deals is None:
                    raise RuntimeError("Collection operation has no deal resolver")
                deal = await self._deals.get(operation.deal_id)
                if deal is None:
                    raise RuntimeError("Collection deal not found")
                prepared = await self._ton.prepare_collection(deal, operation.comment)
            else:
                await self._balances.ensure_available(operation.currency, operation.amount_atomic)
                prepared = await self._ton.prepare_guarant_payout(
                    [
                        PayoutMessage(
                            destination=operation.destination,
                            amount_atomic=operation.amount_atomic,
                            comment=operation.comment,
                            currency=operation.currency,
                        )
                    ]
                )
            attempt = await self._operations.prepare_attempt(operation.id, prepared)
            if attempt is None:
                return
        except Exception as exc:
            await self._operations.schedule_unprepared_retry(
                operation.id, f"prepare: {type(exc).__name__}: {exc}"
            )
            return

        try:
            await self._ton.broadcast(attempt.signed_boc)
        except Exception:
            # A transport exception does not prove rejection. Mark submitted and
            # reconcile the immutable external hash before any further decision.
            self._logger.exception("Broadcast outcome is uncertain operation=%s", operation.id)
        await self._operations.mark_submitted(attempt.id)

    async def _reconcile(
        self,
        operation: FinancialOperation,
        attempt: FinancialOperationAttempt,
    ) -> None:
        result = await self._ton.get_financial_operation_trace_status(operation, attempt)
        match result.status:
            case TraceStatus.CONFIRMED:
                if result.transaction_hash:
                    confirmed = await self._operations.mark_confirmed(
                        attempt.id, result.transaction_hash
                    )
                    if confirmed is not None and self._on_confirmed is not None:
                        await self._on_confirmed(confirmed)
                else:
                    await self._operations.schedule_retry(
                        attempt.id,
                        "Confirmed trace has no transaction hash",
                        uncertain=True,
                    )
            case TraceStatus.BOUNCED:
                await self._operations.schedule_retry(
                    attempt.id, "Transfer bounced", bounced=True
                )
            case TraceStatus.FAILED:
                await self._operations.schedule_retry(
                    attempt.id, "Trace proves transfer execution failure"
                )
            case TraceStatus.NOT_FOUND | TraceStatus.PENDING:
                if (
                    attempt.status is FinancialAttemptStatus.PREPARED
                    and datetime.now(UTC) <= attempt.valid_until
                ):
                    try:
                        await self._ton.broadcast(attempt.signed_boc)
                    except Exception:
                        self._logger.exception(
                            "Prepared BOC rebroadcast outcome is uncertain operation=%s",
                            operation.id,
                        )
                    await self._operations.mark_submitted(attempt.id)
                    return
                if datetime.now(UTC) > attempt.valid_until + timedelta(
                    seconds=self._settings.TON_TRACE_GRACE_SECONDS
                ):
                    await self._operations.schedule_retry(
                        attempt.id,
                        "Broadcast transaction is not provably finalized; manual on-chain review required",
                        uncertain=True,
                    )
