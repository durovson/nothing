from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import DealStatus
from app.core.types import (
    DealRepositoryProtocol,
    TonGatewayProtocol,
)
from app.models.entities import Deal
from app.services.collections import CollectionService

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        ton: TonGatewayProtocol,
        collections: CollectionService,
    ):
        self._settings = settings
        self._deals = deals
        self._ton = ton
        self._collections = collections

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

        await self._collections.start_collection(paid_deal)

    async def _expire_if_needed(self, deal: Deal) -> None:
        started_at = deal.updated_at or deal.created_at
        if not started_at:
            return
        deadline = started_at + timedelta(seconds=self._settings.DEAL_PAYMENT_TIMEOUT_SECONDS)
        if datetime.now(UTC) >= deadline:
            expired = await self._deals.expire_unpaid(deal.id)
            if expired.status is DealStatus.CANCELLED:
                logger.info("Payment window expired for deal %s", expired.public_id)
