from __future__ import annotations

import logging

from app.config import Settings
from app.core.enums import DealStatus
from app.core.exceptions import MissingPayoutWalletError
from app.core.types import (
    DealRepositoryProtocol,
    FinancialOperationRepositoryProtocol,
    NotificationGatewayProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, FinancialOperation, User
from app.ton.amounts import asset_amount_atomic, asset_service_fee_atomic

logger = logging.getLogger(__name__)


class RefundService:
    """Plans buyer and service-fee refund legs without sending a batch."""

    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        operations: FinancialOperationRepositoryProtocol,
        users: UserRepositoryProtocol,
        ton: TonGatewayProtocol,
        notifications: NotificationGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._operations = operations
        self._users = users
        self._ton = ton
        self._notifications = notifications

    async def process_requested(self) -> None:
        deals = await self._deals.list_refund_requested(limit=20)
        buyer_ids = {
            deal.buyer_id
            for deal in deals
            if deal.buyer_id is not None
        }
        buyers = await self._users.get_many(buyer_ids)
        for deal in deals:
            try:
                await self.start_refund(
                    deal,
                    buyers.get(deal.buyer_id) if deal.buyer_id else None,
                )
            except Exception:
                logger.exception("Refund planning failed for deal=%s", deal.public_id)

    async def start_refund(self, deal: Deal, buyer: User | None = None) -> None:
        if buyer is None and deal.buyer_id:
            buyer = await self._users.get(deal.buyer_id)
        refund_wallet = (
            deal.buyer_wallet_snapshot
            or deal.buyer_wallet_address
            or (buyer.wallet_address if buyer else None)
        )
        if buyer is None or refund_wallet is None:
            raise MissingPayoutWalletError(f"Buyer refund wallet is missing for {deal.public_id}")
        await self._operations.plan_refund(
            deal_id=deal.id,
            buyer_destination=self._ton.normalize_address(refund_wallet),
            buyer_amount_atomic=asset_amount_atomic(deal.amount, deal.currency),
            buyer_comment=f"Refund for deal {deal.public_id}",
            service_destination=self._ton.normalize_address(
                self._settings.SERVICE_FEE_WALLET
            ),
            service_amount_atomic=asset_service_fee_atomic(
                deal.amount, deal.currency, self._settings.ESCROW_FEE_RATE
            ),
            service_comment=self._settings.SERVICE_FEE_COMMENT,
        )

    async def on_operation_confirmed(self, operation: FinancialOperation) -> None:
        if operation.deal_id is None:
            return
        deal = await self._deals.get(operation.deal_id)
        if deal is None or deal.status is not DealStatus.REFUNDED:
            return
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        seller = await self._users.get(deal.creator_id)
        await self._notifications.refund_confirmed(deal, buyer, seller)
