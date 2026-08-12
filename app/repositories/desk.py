from __future__ import annotations

from datetime import datetime

from app.database import SupabaseDatabase
from app.models.dto import CreateDeskListingCommand
from app.models.entities import DeskListing, ObservedDeposit


class DeskRepository:
    """Persistence boundary for paid Desk listings and their state machine."""

    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def create(self, command: CreateDeskListingCommand) -> DeskListing:
        response = await self._database.rpc(
            "create_desk_listing",
            {
                "p_public_id": command.public_id,
                "p_owner_id": command.owner_id,
                "p_owner_username": command.owner_username,
                "p_owner_language": command.owner_language.value,
                "p_kind": command.kind.value,
                "p_description": command.description,
                "p_deal_currency": command.deal_currency.value,
                "p_price": str(command.price) if command.price is not None else None,
                "p_payment_currency": command.payment_currency.value,
                "p_publication_fee": str(command.publication_fee),
                "p_publication_fee_atomic": command.publication_fee_atomic,
                "p_payment_deadline_at": command.payment_deadline_at.isoformat(),
            },
        )
        if not response.data:
            raise RuntimeError("Desk listing was not created")
        return DeskListing(**response.data[0])

    async def find_waiting_by_username(
        self, username: str, currency: str
    ) -> DeskListing | None:
        response = await self._database.read(
            lambda: self._database.client.table("desk_listings")
            .select("*")
            .ilike("owner_username", username)
            .eq("payment_currency", currency)
            .eq("status", "waiting_payment")
            .order("id", desc=True)
            .limit(1)
            .execute(),
            name="desk:list-waiting-by-username",
        )
        return DeskListing(**response.data[0]) if response.data else None

    async def find_waiting_by_sender(
        self, sender: str, currency: str
    ) -> DeskListing | None:
        response = await self._database.rpc(
            "find_desk_listing_by_sender",
            {"p_sender": sender, "p_currency": currency},
        )
        return DeskListing(**response.data[0]) if response.data else None

    async def claim_payment(
        self, listing_id: int, deposit: ObservedDeposit
    ) -> DeskListing | None:
        response = await self._database.rpc(
            "claim_desk_listing_payment",
            {
                "p_listing_id": listing_id,
                "p_observed_deposit_id": deposit.id,
                "p_tx_hash": deposit.tx_hash,
                "p_tx_lt": deposit.tx_lt,
                "p_sender": deposit.sender,
                "p_amount_atomic": deposit.amount_atomic,
            },
        )
        return DeskListing(**response.data[0]) if response.data else None

    async def mark_published(self, listing_id: int, message_id: int) -> DeskListing | None:
        response = await self._database.rpc(
            "mark_desk_listing_published",
            {"p_listing_id": listing_id, "p_topic_message_id": message_id},
        )
        return DeskListing(**response.data[0]) if response.data else None

    async def mark_publication_failed(self, listing_id: int, reason: str) -> None:
        await self._database.run(
            lambda: self._database.client.table("desk_listings")
            .update({"status": "publication_failed", "failure_reason": reason[:1000]})
            .eq("id", listing_id)
            .eq("status", "publishing")
            .execute(),
            name="desk:mark-publication-failed",
        )

    async def expire_due(self) -> int:
        response = await self._database.rpc("expire_due_desk_listings", {})
        return int(response.data or 0)

    async def get(self, listing_id: int) -> DeskListing | None:
        response = await self._database.read(
            lambda: self._database.client.table("desk_listings")
            .select("*").eq("id", listing_id).limit(1).execute(),
            name="desk:get",
        )
        return DeskListing(**response.data[0]) if response.data else None

    async def get_by_deposit(self, deposit_id: int) -> DeskListing | None:
        response = await self._database.read(
            lambda: self._database.client.table("desk_listings")
            .select("*").eq("observed_deposit_id", deposit_id).limit(1).execute(),
            name="desk:get-by-deposit",
        )
        return DeskListing(**response.data[0]) if response.data else None

    async def list_publishing(self, limit: int = 20) -> list[DeskListing]:
        response = await self._database.read(
            lambda: self._database.client.table("desk_listings")
            .select("*").eq("status", "publishing").order("id").limit(limit).execute(),
            name="desk:list-publishing",
        )
        return [DeskListing(**row) for row in response.data or []]

    async def plan_invalid_refund(
        self, deposit: ObservedDeposit, reason: str
    ) -> None:
        await self._database.rpc(
            "plan_desk_invalid_payment_refund",
            {"p_observed_deposit_id": deposit.id, "p_reason": reason},
        )
