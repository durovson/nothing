from datetime import UTC, datetime, timedelta

from app.core.constants import (
    GIFT_INSPECTION_TIMEOUT_SECONDS,
    LONG_INSPECTION_TIMEOUT_SECONDS,
)
from app.core.enums import DealStatus, DealType
from app.core.exceptions import DealActionForbiddenError, DealNotFoundError
from app.core.types import (
    DealRepositoryProtocol,
    DisputeRepositoryProtocol,
    NotificationGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import Deal, DisputeTicket, User


class DealLifecycleService:
    def __init__(
        self,
        deals: DealRepositoryProtocol,
        disputes: DisputeRepositoryProtocol,
        users: UserRepositoryProtocol,
        notifications: NotificationGatewayProtocol,
    ):
        self._deals = deals
        self._disputes = disputes
        self._users = users
        self._notifications = notifications

    async def mark_delivered(self, deal_id: int, seller_id: int) -> Deal:
        deal = await self._deals.get(deal_id)
        if deal is None:
            raise DealNotFoundError(f"Deal {deal_id} not found")
        if deal.deal_type is DealType.CHANNEL:
            raise DealActionForbiddenError(
                "Channel delivery is confirmed only by Telegram owner status"
            )
        if deal.creator_id != seller_id or deal.status is not DealStatus.DELIVERY_PENDING:
            raise DealActionForbiddenError("Only the seller can mark an active deal delivered")
        timeout = (
            GIFT_INSPECTION_TIMEOUT_SECONDS
            if deal.deal_type is DealType.GIFTS
            else LONG_INSPECTION_TIMEOUT_SECONDS
        )
        delivered = await self._deals.mark_delivered(
            deal.id,
            seller_id,
            datetime.now(UTC) + timedelta(seconds=timeout),
        )
        if delivered is None:
            raise DealActionForbiddenError("Delivery deadline has expired")
        await self._notify_delivery(delivered)
        return delivered

    async def open_dispute(
        self,
        deal_id: int,
        actor_id: int,
        description: str,
    ) -> DisputeTicket:
        ticket = await self._disputes.open(deal_id, actor_id, description)
        if ticket is None:
            raise DealActionForbiddenError("Dispute cannot be opened for this deal")
        deal = await self._deals.get(deal_id)
        if deal:
            buyer, seller = await self._participants(deal)
            await self._notifications.dispute_opened(deal, buyer, seller)
        return ticket

    async def process_deadlines(self) -> None:
        await self._deals.process_deadlines_batch(limit=50)

    async def _notify_delivery(self, deal: Deal) -> None:
        buyer, seller = await self._participants(deal)
        await self._notifications.delivery_marked(deal, buyer, seller)

    async def _participants(self, deal: Deal) -> tuple[User | None, User | None]:
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        seller = await self._users.get(deal.creator_id)
        return buyer, seller
