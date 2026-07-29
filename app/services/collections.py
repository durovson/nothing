from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.constants import SELLER_DELIVERY_TIMEOUT_SECONDS
from app.core.enums import Currency, DealStatus
from app.core.types import (
    DealRepositoryProtocol,
    FinancialOperationRepositoryProtocol,
    NotificationGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, FinancialOperation
from app.services.channels import ChannelDealService


class CollectionService:
    """Plans escrow custody; the shared financial processor executes it."""

    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        operations: FinancialOperationRepositoryProtocol,
        users: UserRepositoryProtocol,
        notifications: NotificationGatewayProtocol,
        channels: ChannelDealService,
        guarant_address: str,
    ):
        self._settings = settings
        self._deals = deals
        self._operations = operations
        self._users = users
        self._notifications = notifications
        self._channels = channels
        self._guarant_address = guarant_address

    async def start_collection(self, deal: Deal) -> FinancialOperation | None:
        if deal.currency is Currency.USDT:
            direct = await self._deals.mark_direct_custody(
                deal.id,
                datetime.now(UTC) + timedelta(seconds=SELLER_DELIVERY_TIMEOUT_SECONDS),
            )
            if direct and direct.status is DealStatus.DELIVERY_PENDING:
                await self._notify_custody(direct)
            return None
        return await self._operations.plan_collection(
            deal_id=deal.id,
            destination=self._guarant_address,
            comment=f"Escrow for deal {deal.public_id}",
        )

    async def start_unmatched_collection(
        self, deal: Deal, unmatched_payment_id: int
    ) -> FinancialOperation | None:
        if deal.currency is not Currency.TON:
            return None
        return await self._operations.plan_collection(
            deal_id=deal.id,
            destination=self._guarant_address,
            comment=f"Recovery for deal {deal.public_id}",
            unmatched_payment_id=unmatched_payment_id,
        )

    async def on_operation_confirmed(self, operation: FinancialOperation) -> None:
        if operation.deal_id is None or operation.metadata.get("purpose") != "deal_custody":
            return
        deal = await self._deals.get(operation.deal_id)
        if deal and deal.status is DealStatus.DELIVERY_PENDING:
            await self._notify_custody(deal)

    async def _notify_custody(self, deal: Deal) -> None:
        seller = await self._users.get(deal.creator_id)
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        await self._notifications.payment_received(deal, buyer, seller)
        await self._channels.process_paid(deal)
