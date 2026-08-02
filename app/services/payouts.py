from __future__ import annotations

import logging
from decimal import Decimal

from app.config import Settings
from app.core.enums import DealStatus, FinancialOperationFlow
from app.core.exceptions import (
    DealConfirmationForbiddenError,
    DealNotFoundError,
    MissingPayoutWalletError,
    ServiceUnavailableError,
)
from app.core.types import (
    DealRepositoryProtocol,
    FinancialOperationRepositoryProtocol,
    NotificationGatewayProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, FinancialOperation, User
from app.services.referrals import ReferralService
from app.services.system_mode import SystemModeService
from app.ton.amounts import asset_amount_atomic, asset_service_fee_atomic

logger = logging.getLogger(__name__)


class PayoutService:
    """Plans payout legs; network execution belongs to the payout processor."""

    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        operations: FinancialOperationRepositoryProtocol,
        users: UserRepositoryProtocol,
        referrals: ReferralService,
        ton: TonGatewayProtocol,
        notifications: NotificationGatewayProtocol,
        system_mode: SystemModeService | None = None,
    ):
        self._settings = settings
        self._deals = deals
        self._operations = operations
        self._users = users
        self._referrals = referrals
        self._ton = ton
        self._notifications = notifications
        self._system_mode = system_mode

    async def confirm_receipt(self, deal_id: int, buyer_id: int) -> Deal:
        if self._system_mode is not None and not await self._system_mode.allows_flow(FinancialOperationFlow.PAYOUT):
            raise ServiceUnavailableError("В аварийном режиме выплаты продавцам приостановлены")
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
        await self.publish_pending_success_feed()
        if self._system_mode is not None and not await self._system_mode.allows_flow(FinancialOperationFlow.PAYOUT):
            return
        deals = await self._deals.list_release_requested(limit=20)
        participant_ids = {
            participant_id
            for deal in deals
            for participant_id in (deal.creator_id, deal.buyer_id)
            if participant_id is not None
        }
        participants = await self._users.get_many(participant_ids)
        for deal in deals:
            try:
                await self.start_payout(
                    deal,
                    seller=participants.get(deal.creator_id),
                    buyer=participants.get(deal.buyer_id) if deal.buyer_id else None,
                )
            except Exception:
                logger.exception("Payout planning failed for deal=%s", deal.public_id)

    async def start_payout(
        self,
        deal: Deal,
        *,
        seller: User | None = None,
        buyer: User | None = None,
    ) -> None:
        if seller is None:
            seller = await self._users.get(deal.creator_id)
        payout_wallet = deal.seller_wallet_address or (seller.wallet_address if seller else None)
        if seller is None or payout_wallet is None:
            raise MissingPayoutWalletError(f"Seller wallet is missing for deal {deal.public_id}")
        if buyer is None and deal.buyer_id:
            buyer = await self._users.get(deal.buyer_id)
        allocations = self._referrals.reward_allocations(seller, buyer, deal)
        referral_total = sum((amount for _, amount in allocations), start=Decimal(0))
        service_fee_atomic = asset_service_fee_atomic(
            deal.amount, deal.currency, self._settings.ESCROW_FEE_RATE
        )
        referral_atomic = (
            asset_amount_atomic(referral_total, deal.currency) if referral_total > 0 else 0
        )
        service_net_atomic = service_fee_atomic - referral_atomic
        await self._operations.plan_payout(
            deal_id=deal.id,
            seller_destination=self._ton.normalize_address(payout_wallet),
            seller_amount_atomic=asset_amount_atomic(deal.amount, deal.currency),
            seller_comment=f"Payment for deal {deal.public_id}",
            service_destination=self._ton.normalize_address(
                self._settings.SERVICE_FEE_WALLET
            ),
            service_amount_atomic=service_net_atomic,
            service_comment=self._settings.SERVICE_FEE_COMMENT,
            referral_allocations=[
                {
                    "referrer_id": participant.referrer_id,
                    "referred_id": participant.telegram_id,
                    "amount": str(amount),
                }
                for participant, amount in allocations
            ],
        )

    async def on_operation_confirmed(self, operation: FinancialOperation) -> None:
        if operation.deal_id is None:
            return
        deal = await self._deals.get(operation.deal_id)
        if deal is None or deal.status is not DealStatus.COMPLETED:
            return
        seller = await self._users.get(deal.creator_id)
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        await self._notifications.payout_confirmed(deal, buyer, seller)
        await self._publish_completed_deal(deal)

    async def publish_pending_success_feed(self) -> None:
        """Retry feed delivery without replaying already claimed publications."""
        for deal in await self._deals.list_completed_without_success_feed(limit=20):
            await self._publish_completed_deal(deal)

    async def _publish_completed_deal(self, deal: Deal) -> None:
        claimed = await self._deals.claim_success_feed_notification(deal.id)
        if claimed is None:
            return
        published = await self._notifications.completed_deal_feed(claimed)
        if not published:
            await self._deals.release_success_feed_notification(deal.id)
