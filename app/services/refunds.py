from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import RefundStatus, TraceStatus
from app.core.exceptions import InsufficientPayoutReserveError, MissingPayoutWalletError
from app.core.types import (
    DealRepositoryProtocol,
    NotificationGatewayProtocol,
    PayoutRepositoryProtocol,
    RefundRepositoryProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, RefundAttempt
from app.ton.amounts import asset_amount_atomic, asset_service_fee_atomic, payout_amount_atomic
from app.ton.models import PayoutMessage

logger = logging.getLogger(__name__)


class RefundService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        refunds: RefundRepositoryProtocol,
        payouts: PayoutRepositoryProtocol,
        users: UserRepositoryProtocol,
        ton: TonGatewayProtocol,
        notifications: NotificationGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._refunds = refunds
        self._payouts = payouts
        self._users = users
        self._ton = ton
        self._notifications = notifications

    async def process_requested(self) -> None:
        if await self._payouts.list_open() or await self._refunds.list_open():
            return
        requested = await self._deals.list_refund_requested(limit=1)
        if requested:
            await self.start_refund(requested[0])

    async def start_refund(self, deal: Deal) -> None:
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        if not buyer or not buyer.wallet_address:
            raise MissingPayoutWalletError(f"Buyer refund wallet is missing for {deal.public_id}")
        destination = self._ton.normalize_address(buyer.wallet_address)
        amount_atomic = asset_amount_atomic(deal.amount, deal.currency)
        reward_atomic = asset_service_fee_atomic(deal.amount, deal.currency, self._settings.ESCROW_FEE_RATE)
        if await self._ton.get_guarant_asset_balance_atomic(deal.currency) < amount_atomic + reward_atomic:
            raise InsufficientPayoutReserveError("Guarant asset balance does not cover refund and service fee")
        gas_required = payout_amount_atomic(self._settings.TON_GUARANT_PAYOUT_GAS_RESERVE)
        if deal.currency.value == "USDT":
            gas_required += 2 * payout_amount_atomic(self._settings.USDT_JETTON_TRANSFER_TON)
        if await self._ton.get_guarant_balance_atomic() < gas_required:
            raise InsufficientPayoutReserveError("Guarant TON balance does not cover refund gas")
        comment = f"Refund for deal {deal.public_id}"
        reason = deal.resolution_reason or "Escrow refund"
        attempt = await self._refunds.claim(
            deal, destination, amount_atomic, comment, reason,
            self._ton.normalize_address(self._settings.SERVICE_FEE_WALLET),
            reward_atomic, self._settings.SERVICE_FEE_COMMENT,
        )
        if attempt is None:
            return
        await self._prepare_and_broadcast(attempt)

    async def reconcile_open(self) -> None:
        for attempt in await self._refunds.list_open():
            try:
                await self.reconcile(attempt)
            except Exception:
                logger.exception("Refund reconciliation failed attempt=%s", attempt.id)

    async def reconcile(self, attempt: RefundAttempt) -> None:
        if attempt.status is RefundStatus.CREATING:
            attempt = await self._prepare(attempt)
        if attempt.status is RefundStatus.PREPARED:
            if not attempt.signed_boc:
                await self._refunds.mark_failed(attempt.id, "Prepared refund has no signed BOC")
                return
            try:
                await self._ton.broadcast(attempt.signed_boc)
            except Exception:
                logger.exception("Refund re-broadcast outcome uncertain attempt=%s", attempt.id)
            attempt = await self._refunds.mark_submitted(attempt.id)
        status = await self._ton.get_refund_trace_status(attempt)
        match status:
            case TraceStatus.CONFIRMED:
                deal = await self._refunds.mark_confirmed(attempt.id)
                if deal:
                    buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
                    seller = await self._users.get(deal.creator_id)
                    await self._notifications.refund_confirmed(deal, buyer, seller)
            case TraceStatus.BOUNCED:
                await self._refunds.mark_bounced(attempt.id, "Refund transfer bounced")
            case TraceStatus.FAILED:
                await self._refunds.mark_failed(attempt.id, "Refund trace execution failed")
            case TraceStatus.NOT_FOUND | TraceStatus.PENDING:
                await self._fail_if_expired(attempt)

    async def _prepare_and_broadcast(self, attempt: RefundAttempt) -> None:
        try:
            attempt = await self._prepare(attempt)
        except Exception as exc:
            await self._refunds.mark_failed(attempt.id, f"prepare: {exc}")
            raise
        try:
            await self._ton.broadcast(attempt.signed_boc or "")
        except Exception:
            logger.exception("Refund broadcast outcome uncertain attempt=%s", attempt.id)
            return
        await self._refunds.mark_submitted(attempt.id)

    async def _prepare(self, attempt: RefundAttempt) -> RefundAttempt:
        prepared = await self._ton.prepare_guarant_payout(
            [
                PayoutMessage(attempt.destination, attempt.amount_atomic, attempt.comment, currency=attempt.currency),
                PayoutMessage(
                    attempt.reward_destination or "",
                    int(attempt.reward_nominal_amount_atomic or 0),
                    attempt.reward_comment or "",
                    currency=attempt.currency,
                ),
            ]
        )
        return await self._refunds.save_prepared(
            attempt.id,
            prepared.normalized_hash,
            prepared.signed_boc,
            prepared.valid_until,
        )

    async def _fail_if_expired(self, attempt: RefundAttempt) -> None:
        if attempt.valid_until and datetime.now(UTC) > attempt.valid_until + timedelta(
            seconds=self._settings.TON_TRACE_GRACE_SECONDS
        ):
            await self._refunds.mark_failed(
                attempt.id,
                "Refund message expired and was not found in TonAPI",
            )
