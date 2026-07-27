from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import DealStatus, PayoutStatus, TraceStatus
from app.core.exceptions import (
    DealConfirmationForbiddenError,
    DealNotFoundError,
    InsufficientPayoutReserveError,
    MissingPayoutWalletError,
)
from app.core.types import (
    DealRepositoryProtocol,
    NotificationGatewayProtocol,
    PayoutRepositoryProtocol,
    RefundRepositoryProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, PayoutAttempt
from app.services.referrals import ReferralService
from app.ton.amounts import asset_amount_atomic, asset_service_fee_atomic, payout_amount_atomic
from app.ton.models import PayoutMessage

logger = logging.getLogger(__name__)


class PayoutService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        payouts: PayoutRepositoryProtocol,
        refunds: RefundRepositoryProtocol,
        users: UserRepositoryProtocol,
        referrals: ReferralService,
        ton: TonGatewayProtocol,
        notifications: NotificationGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._payouts = payouts
        self._refunds = refunds
        self._users = users
        self._referrals = referrals
        self._ton = ton
        self._notifications = notifications

    async def confirm_receipt(self, deal_id: int, buyer_id: int) -> Deal:
        deal = await self._deals.get(deal_id)
        if not deal:
            raise DealNotFoundError(f"Deal {deal_id} not found")
        if deal.buyer_id != buyer_id or deal.status is not DealStatus.DELIVERED:
            raise DealConfirmationForbiddenError("Only the buyer can confirm a paid deal")
        requested = await self._deals.request_release(deal.id, buyer_id)
        if requested is None:
            raise DealConfirmationForbiddenError("Deal release could not be requested")
        return requested

    async def process_releases(self) -> None:
        if await self._payouts.list_open() or await self._refunds.list_open():
            return
        requested = await self._deals.list_release_requested(limit=1)
        if requested:
            await self.start_payout(requested[0])

    async def start_payout(self, deal: Deal) -> None:
        seller = await self._users.get(deal.creator_id)
        if not seller or not seller.wallet_address:
            raise MissingPayoutWalletError(f"Seller wallet is missing for deal {deal.public_id}")

        seller_destination = self._ton.normalize_address(seller.wallet_address)
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        seller_amount_atomic = asset_amount_atomic(deal.amount, deal.currency)
        service_fee_atomic = asset_service_fee_atomic(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
        )
        referral_reserved_atomic = asset_amount_atomic(
            self._referrals.reward_total(seller, buyer, deal), deal.currency
        )
        reward_nominal_amount_atomic = service_fee_atomic - referral_reserved_atomic
        reward_destination = (
            self._ton.normalize_address(self._settings.SERVICE_FEE_WALLET)
            if reward_nominal_amount_atomic > 0 else None
        )
        reward_comment = self._settings.SERVICE_FEE_COMMENT if reward_destination else None
        if await self._ton.get_guarant_asset_balance_atomic(deal.currency) < (
            seller_amount_atomic + reward_nominal_amount_atomic
        ):
            raise InsufficientPayoutReserveError(
                "Guarant asset balance does not cover seller and service fee"
            )
        gas_required = payout_amount_atomic(self._settings.TON_GUARANT_PAYOUT_GAS_RESERVE)
        if deal.currency.value == "USDT":
            message_count = 2 if reward_destination else 1
            gas_required += message_count * payout_amount_atomic(self._settings.USDT_JETTON_TRANSFER_TON)
        if await self._ton.get_guarant_balance_atomic() < gas_required:
            raise InsufficientPayoutReserveError("Guarant TON balance does not cover payout gas")
        seller_comment = f"Payment for deal {deal.public_id}"

        attempt = await self._payouts.claim(
            deal,
            seller_destination,
            seller_amount_atomic,
            seller_comment,
            reward_destination,
            reward_nominal_amount_atomic,
            reward_comment,
        )
        if attempt is None:
            logger.info("Payout already claimed for deal %s", deal.public_id)
            return

        try:
            prepared = await self._ton.prepare_guarant_payout(
                self._messages(attempt)
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
        if attempt.status is PayoutStatus.CREATING:
            prepared = await self._ton.prepare_guarant_payout(
                self._messages(attempt)
            )
            attempt = await self._payouts.save_prepared(
                attempt.id,
                prepared.normalized_hash,
                prepared.signed_boc,
                prepared.valid_until,
            )

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

        trace_status = await self._ton.get_payout_trace_status(attempt)
        match trace_status:
            case TraceStatus.CONFIRMED:
                deal = await self._deals.get(attempt.deal_id)
                if deal:
                    seller = await self._users.get(deal.creator_id)
                    buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
                    await self._referrals.apply_reward(seller, buyer, deal)
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
        await self._notifications.payout_confirmed(deal, buyer, seller)

    @staticmethod
    def _messages(attempt: PayoutAttempt) -> list[PayoutMessage]:
        messages = [PayoutMessage(
            attempt.destination, attempt.amount_atomic, attempt.comment,
            currency=attempt.currency,
        )]
        reward_fields = (
            attempt.reward_destination,
            attempt.reward_nominal_amount_atomic,
            attempt.reward_comment,
        )
        if all(reward_fields):
            messages.append(PayoutMessage(
                str(attempt.reward_destination), int(attempt.reward_nominal_amount_atomic or 0),
                str(attempt.reward_comment), currency=attempt.currency,
            ))
        elif any(reward_fields):
            raise ValueError("Payout has incomplete service reward data")
        return messages
