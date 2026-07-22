from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import DealStatus
from app.core.exceptions import MissingPayoutWalletError
from app.core.types import (
    DealRepositoryProtocol,
    NotificationGatewayProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal
from app.services.payouts import PayoutService

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        users: UserRepositoryProtocol,
        ton: TonGatewayProtocol,
        payouts: PayoutService,
        notifications: NotificationGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._users = users
        self._ton = ton
        self._payouts = payouts
        self._notifications = notifications

    async def process_pending(self) -> None:
        for deal in await self._deals.list_pending():
            try:
                await self.check_deal(deal)
            except Exception:
                logger.exception("Payment polling failed for deal %s", deal.public_id)

    async def check_deal(self, deal: Deal) -> None:
        payment = await self._ton.find_incoming_payment(deal)
        if payment is None:
            await self._expire_if_needed(deal)
            return

        paid_deal = await self._deals.claim_payment(deal.id, payment)
        if paid_deal is None:
            logger.info("Payment %s was already claimed", payment.tx_hash)
            return

        seller = await self._users.get(paid_deal.creator_id)
        buyer = await self._users.get(paid_deal.buyer_id) if paid_deal.buyer_id else None
        await self._notifications.payment_received(paid_deal, buyer, seller)

        if self._settings.AUTO_PAYOUT_AFTER_PAYMENT:
            try:
                await self._payouts.start_payout(paid_deal)
            except MissingPayoutWalletError:
                logger.warning("Automatic payout waits for seller wallet, deal=%s", paid_deal.public_id)

    async def _expire_if_needed(self, deal: Deal) -> None:
        started_at = deal.updated_at or deal.created_at
        if not started_at:
            return
        deadline = started_at + timedelta(seconds=self._settings.DEAL_PAYMENT_TIMEOUT_SECONDS)
        if datetime.now(UTC) >= deadline:
            expired = await self._deals.expire_unpaid(deal.id)
            if expired.status is DealStatus.CANCELLED:
                logger.info("Payment window expired for deal %s", expired.public_id)

