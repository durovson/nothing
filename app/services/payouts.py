from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import DealStatus, PayoutStatus, TraceStatus
from app.core.exceptions import (
    DealConfirmationForbiddenError,
    DealNotFoundError,
    MissingPayoutWalletError,
)
from app.core.types import (
    DealRepositoryProtocol,
    NotificationGatewayProtocol,
    PayoutRepositoryProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, PayoutAttempt
from app.services.referrals import ReferralService
from app.ton.amounts import payout_amount_atomic
from app.ton.models import PayoutMessage

logger = logging.getLogger(__name__)


class PayoutService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        payouts: PayoutRepositoryProtocol,
        users: UserRepositoryProtocol,
        referrals: ReferralService,
        ton: TonGatewayProtocol,
        notifications: NotificationGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._payouts = payouts
        self._users = users
        self._referrals = referrals
        self._ton = ton
        self._notifications = notifications

    async def confirm_receipt(self, deal_id: int, buyer_id: int) -> Deal:
        deal = await self._deals.get(deal_id)
        if not deal:
            raise DealNotFoundError(f"Deal {deal_id} not found")
        if deal.buyer_id != buyer_id or deal.status is not DealStatus.PAID:
            raise DealConfirmationForbiddenError("Only the buyer can confirm a paid deal")
        await self.start_payout(deal)
        return await self._deals.get(deal.id) or deal

    async def start_payout(self, deal: Deal) -> None:
        seller = await self._users.get(deal.creator_id)
        if not seller or not seller.wallet_address:
            raise MissingPayoutWalletError(f"Seller wallet is missing for deal {deal.public_id}")

        attempt = await self._payouts.claim(
            deal,
            seller.wallet_address,
            payout_amount_atomic(deal.amount),
            f"Payment for deal {deal.public_id}",
        )
        if attempt is None:
            logger.info("Payout already claimed for deal %s", deal.public_id)
            return

        try:
            prepared = await self._ton.prepare_batch_payout(
                deal.subwallet_id,
                [PayoutMessage(attempt.destination, attempt.amount_atomic, attempt.comment)],
            )
            attempt = await self._payouts.save_prepared(
                attempt.id,
                prepared.normalized_hash,
                prepared.signed_boc,
                prepared.valid_until,
            )
        except Exception as exc:
            await self._payouts.mark_failed(attempt.id, f"prepare: {exc}")
            raise

        try:
            await self._ton.broadcast(attempt.signed_boc or "")
        except Exception:
            logger.exception("Broadcast outcome is uncertain for payout %s", attempt.id)
            return
        await self._payouts.mark_submitted(attempt.id)

    async def reconcile_open(self) -> None:
        for attempt in await self._payouts.list_open():
            try:
                await self.reconcile(attempt)
            except Exception:
                logger.exception("Payout reconciliation failed for attempt %s", attempt.id)

    async def reconcile(self, attempt: PayoutAttempt) -> None:
        if attempt.status is PayoutStatus.PREPARED:
            if not attempt.signed_boc:
                await self._payouts.mark_failed(attempt.id, "Prepared payout has no signed BOC")
                return
            try:
                await self._ton.broadcast(attempt.signed_boc)
            except Exception:
                logger.exception("Re-broadcast outcome is uncertain for payout %s", attempt.id)
            attempt = await self._payouts.mark_submitted(attempt.id)

        if not attempt.external_message_hash:
            await self._payouts.mark_failed(attempt.id, "Submitted payout has no message hash")
            return

        trace_status = await self._ton.get_trace_status(attempt.external_message_hash)
        match trace_status:
            case TraceStatus.CONFIRMED:
                completed = await self._payouts.mark_confirmed(attempt.id)
                if completed:
                    await self._on_confirmed(completed)
            case TraceStatus.BOUNCED:
                await self._payouts.mark_bounced(attempt.id, "TonAPI trace contains a bounced message")
            case TraceStatus.FAILED:
                await self._payouts.mark_failed(attempt.id, "TonAPI trace execution failed")
            case TraceStatus.NOT_FOUND | TraceStatus.PENDING:
                await self._fail_if_expired(attempt)

    async def _fail_if_expired(self, attempt: PayoutAttempt) -> None:
        if not attempt.valid_until:
            return
        deadline = attempt.valid_until + timedelta(seconds=self._settings.TON_TRACE_GRACE_SECONDS)
        if datetime.now(UTC) > deadline:
            await self._payouts.mark_failed(
                attempt.id,
                "External message expired and was not found in TonAPI",
            )

    async def _on_confirmed(self, deal: Deal) -> None:
        seller = await self._users.get(deal.creator_id)
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        await self._referrals.apply_reward(seller, buyer, deal)
        await self._notifications.payout_confirmed(deal, buyer, seller)
