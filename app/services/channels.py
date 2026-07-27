from __future__ import annotations

import logging

from app.api.channel_gateway import TelegramChannelGateway
from app.core.enums import DealType
from app.core.types import DealRepositoryProtocol, UserRepositoryProtocol
from app.models.dto import ChannelDescriptor
from app.models.entities import Deal

logger = logging.getLogger(__name__)


class ChannelAccessService:
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
        if deal.channel_access_granted_at:
            await self._deals.request_channel_release(deal.id)
            return True
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        seller = await self._users.get(deal.creator_id)
        if buyer is None:
            await self._deals.record_channel_access_error(deal.id, "Buyer not found")
            return False
        try:
            granted = await self._gateway.grant_buyer_admin(deal)
            if not granted:
                waiting_reason = "Waiting for buyer join request"
                if deal.channel_access_error != waiting_reason:
                    invite = await self._gateway.create_buyer_join_link(deal)
                    await self._gateway.access_required(deal, buyer, invite)
                    await self._deals.record_channel_access_error(deal.id, waiting_reason)
                return False
            updated = await self._deals.mark_channel_access_granted(deal.id)
            if updated is None:
                return False
            await self._gateway.access_granted(updated, buyer, seller)
            await self._deals.request_channel_release(updated.id)
            return True
        except Exception as exc:
            await self._deals.record_channel_access_error(deal.id, str(exc))
            logger.exception("Channel access failed deal=%s", deal.public_id)
            return False

    async def process_pending(self) -> None:
        for deal in await self._deals.list_channel_access_pending():
            await self.process_paid(deal)
