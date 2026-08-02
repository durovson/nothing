from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.api.channel_gateway import TelegramChannelGateway
from app.core.enums import ChannelMemberStatus, DealType
from app.core.types import DealRepositoryProtocol, UserRepositoryProtocol
from app.models.dto import ChannelDescriptor
from app.models.entities import Deal, User

logger = logging.getLogger(__name__)


class ChannelDealService:
    """Poll Telegram ownership and drive only atomic channel transitions."""
    def __init__(
        self,
        deals: DealRepositoryProtocol,
        users: UserRepositoryProtocol,
        gateway: TelegramChannelGateway,
    ):
        self._deals = deals
        self._users = users
        self._gateway = gateway

    async def validate_for_sale(
        self, channel_reference: int | str, seller_id: int
    ) -> ChannelDescriptor:
        return await self._gateway.validate_for_sale(channel_reference, seller_id)

    async def buyer_join_link(self, deal: Deal) -> str | None:
        if deal.deal_type is not DealType.CHANNEL:
            return None
        return await self._gateway.create_buyer_join_link(deal)

    async def process_paid(self, deal: Deal) -> bool:
        if deal.deal_type is not DealType.CHANNEL:
            return False
        return await self.check_transfer(deal)

    async def check_transfer(
        self,
        deal: Deal,
        participants: tuple[User | None, User | None] | None = None,
    ) -> bool:
        """Release only for creator; dispute a non-owner only after the SLA."""
        if participants is None:
            buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
            seller = await self._users.get(deal.creator_id)
        else:
            buyer, seller = participants
        if buyer is None:
            await self._deals.record_channel_observation(
                deal.id, ChannelMemberStatus.UNKNOWN.value, "Buyer not found"
            )
            return False
        status = ChannelMemberStatus.UNKNOWN
        try:
            status = await self._gateway.buyer_status(deal)
            await self._deals.record_channel_observation(deal.id, status.value)
            if status is ChannelMemberStatus.OWNER:
                completed = await self._deals.confirm_channel_owner(deal.id)
                if completed:
                    await self._gateway.owner_verified(completed, buyer, seller)
                    return True
                return False
            if (
                status is not ChannelMemberStatus.OWNER
                and deal.delivery_deadline_at
                and deal.delivery_deadline_at <= datetime.now(UTC)
            ):
                reason = f"Buyer Telegram status at deadline: {status.value}; owner required"
                disputed = await self._deals.dispute_channel_transfer(deal.id, reason)
                if disputed:
                    await self._gateway.transfer_disputed(disputed, buyer, seller)
            return False
        except Exception as exc:
            await self._deals.record_channel_observation(
                deal.id, ChannelMemberStatus.UNKNOWN.value, str(exc)
            )
            logger.exception("Channel ownership check failed deal=%s", deal.public_id)
            if deal.delivery_deadline_at and deal.delivery_deadline_at <= datetime.now(UTC):
                disputed = await self._deals.dispute_channel_transfer(
                    deal.id,
                    "Telegram ownership verification unavailable at deadline",
                )
                if disputed:
                    await self._gateway.transfer_disputed(disputed, buyer, seller)
            return False

    async def process_pending(self) -> None:
        deals = await self._deals.list_channel_transfer_pending(limit=20)
        participant_ids = {
            participant_id
            for deal in deals
            for participant_id in (deal.creator_id, deal.buyer_id)
            if participant_id is not None
        }
        participants = await self._users.get_many(participant_ids)
        for deal in deals:
            await self.check_transfer(
                deal,
                (
                    participants.get(deal.buyer_id) if deal.buyer_id else None,
                    participants.get(deal.creator_id),
                ),
            )
