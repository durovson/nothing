from __future__ import annotations

import asyncio
from decimal import Decimal
from math import ceil
from time import monotonic

from app.core.constants import OTC_OFFER_COOLDOWN_SECONDS
from app.core.exceptions import (
    OtcOfferCooldownError,
    OtcOfferResolutionError,
    OtcOfferUnavailableError,
)
from app.models.dto import CreateOtcOfferCommand
from app.models.entities import DeskListing, OtcOffer, User
from app.repositories.desk import DeskRepository
from app.repositories.otc_offers import OtcOfferRepository


class OtcOfferService:
    """Negotiation-only OTC offers; no assets or escrow are moved here."""

    def __init__(
        self,
        offers: OtcOfferRepository,
        listings: DeskRepository,
    ):
        self._offers = offers
        self._listings = listings
        self._cooldowns: dict[int, float] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    async def prepare(self, listing_public_id: str, buyer_id: int) -> DeskListing:
        listing = await self._listings.get_published_by_public_id(listing_public_id)
        if listing is None or listing.owner_id == buyer_id:
            raise OtcOfferUnavailableError
        return listing

    async def create(
        self,
        listing_public_id: str,
        buyer: User,
        amount: Decimal,
    ) -> OtcOffer:
        lock = self._locks.setdefault(buyer.telegram_id, asyncio.Lock())
        async with lock:
            now = monotonic()
            deadline = self._cooldowns.get(buyer.telegram_id, 0)
            if deadline > now:
                raise OtcOfferCooldownError(ceil(deadline - now))

            offer = await self._offers.create(
                CreateOtcOfferCommand(
                    listing_public_id=listing_public_id,
                    buyer_id=buyer.telegram_id,
                    buyer_username=buyer.username,
                    buyer_language=buyer.language,
                    amount=amount,
                )
            )
            if offer is None:
                raise OtcOfferUnavailableError

            self._cooldowns[buyer.telegram_id] = (
                now + OTC_OFFER_COOLDOWN_SECONDS
            )
            if len(self._cooldowns) > 10_000:
                self._cooldowns = {
                    user_id: expires_at
                    for user_id, expires_at in self._cooldowns.items()
                    if expires_at > now
                }
                self._locks = {
                    user_id: user_lock
                    for user_id, user_lock in self._locks.items()
                    if user_id in self._cooldowns or user_lock.locked()
                }
            return offer

    async def resolve(
        self, offer_id: int, seller_id: int, *, accepted: bool
    ) -> OtcOffer:
        offer = await self._offers.resolve(
            offer_id, seller_id, accepted=accepted
        )
        if offer is None:
            raise OtcOfferResolutionError
        return offer
