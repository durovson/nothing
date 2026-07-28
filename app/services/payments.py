from __future__ import annotations

import logging
from app.config import Settings
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
            return

        paid_deal = await self._deals.claim_payment(deal.id, payment)
        if paid_deal is None:
            logger.info("Payment %s was already claimed", payment.tx_hash)
            return

        await self._collections.start_collection(paid_deal)
