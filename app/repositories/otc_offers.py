from __future__ import annotations

from app.database import SupabaseDatabase
from app.models.dto import CreateOtcOfferCommand
from app.models.entities import OtcOffer


class OtcOfferRepository:
    """Persistence boundary for the lightweight Desk negotiation flow."""

    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def create(self, command: CreateOtcOfferCommand) -> OtcOffer | None:
        response = await self._database.rpc(
            "create_otc_offer",
            {
                "p_listing_public_id": command.listing_public_id,
                "p_buyer_id": command.buyer_id,
                "p_buyer_username": command.buyer_username,
                "p_buyer_language": command.buyer_language.value,
                "p_amount": str(command.amount),
            },
        )
        return OtcOffer(**response.data[0]) if response.data else None

    async def resolve(
        self, offer_id: int, seller_id: int, *, accepted: bool
    ) -> OtcOffer | None:
        response = await self._database.rpc(
            "resolve_otc_offer",
            {
                "p_offer_id": offer_id,
                "p_seller_id": seller_id,
                "p_status": "accepted" if accepted else "declined",
            },
        )
        return OtcOffer(**response.data[0]) if response.data else None
