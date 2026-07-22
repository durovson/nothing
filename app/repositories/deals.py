from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from app.core.enums import DealStatus
from app.core.exceptions import DealNotFoundError
from app.database import SupabaseDatabase
from app.models.dto import CreateDealCommand, PaymentObservation
from app.models.entities import Deal


def _serialize(changes: dict[str, object]) -> dict[str, object]:
    return {
        key: value.value if isinstance(value, Enum) else str(value) if isinstance(value, Decimal) else value
        for key, value in changes.items()
    }


class DealRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def create(self, command: CreateDealCommand) -> Deal:
        response = await self._database.run(
            lambda: self._database.client.table("deals")
            .insert(
                {
                    "creator_id": command.creator_id,
                    "public_id": command.public_id,
                    "deal_type": command.deal_type.value,
                    "description": command.description,
                    "currency": command.currency.value,
                    "amount": str(command.amount),
                    "status": DealStatus.CREATING.value,
                }
            )
            .execute()
        )
        return Deal(**response.data[0])

    async def activate(self, deal_id: int, wallet_address: str) -> Deal:
        return await self.transition(
            deal_id,
            DealStatus.CREATING,
            status=DealStatus.PENDING,
            wallet_address=wallet_address,
            failure_reason=None,
        )

    async def mark_creation_failed(self, deal_id: int, reason: str) -> Deal:
        return await self.transition(
            deal_id,
            DealStatus.CREATING,
            status=DealStatus.CREATION_FAILED,
            failure_reason=reason[:1_000],
        )

    async def transition(
        self,
        deal_id: int,
        expected: DealStatus,
        **changes: object,
    ) -> Deal:
        serialized = _serialize(changes)
        serialized["updated_at"] = datetime.now(UTC).isoformat()
        response = await self._database.run(
            lambda: self._database.client.table("deals")
            .update(serialized)
            .eq("id", deal_id)
            .eq("status", expected.value)
            .execute()
        )
        if response.data:
            return Deal(**response.data[0])
        current = await self.get(deal_id)
        if current is None:
            raise DealNotFoundError(f"Deal {deal_id} not found")
        return current

    async def get(self, deal_id: int) -> Deal | None:
        response = await self._database.run(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("id", deal_id)
            .limit(1)
            .execute()
        )
        return Deal(**response.data[0]) if response.data else None

    async def get_by_public_id(self, public_id: str) -> Deal | None:
        response = await self._database.run(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("public_id", public_id)
            .limit(1)
            .execute()
        )
        return Deal(**response.data[0]) if response.data else None

    async def join(self, public_id: str, buyer_id: int) -> Deal | None:
        response = await self._database.rpc(
            "claim_deal_buyer",
            {"p_public_id": public_id, "p_buyer_id": buyer_id},
        )
        return Deal(**response.data[0]) if response.data else None

    async def claim_payment(self, deal_id: int, payment: PaymentObservation) -> Deal | None:
        response = await self._database.rpc(
            "claim_deal_payment",
            {
                "p_deal_id": deal_id,
                "p_tx_hash": payment.tx_hash,
                "p_tx_lt": payment.tx_lt,
                "p_amount_atomic": payment.amount_atomic,
                "p_sender": payment.sender,
                "p_observed_at": payment.observed_at.isoformat(),
            },
        )
        return Deal(**response.data[0]) if response.data else None

    async def list_for_user(
        self,
        telegram_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[Deal], bool]:
        offset = page * page_size
        response = await self._database.run(
            lambda: self._database.client.table("deals")
            .select("*")
            .or_(f"creator_id.eq.{telegram_id},buyer_id.eq.{telegram_id}")
            .order("id", desc=True)
            .range(offset, offset + page_size)
            .execute()
        )
        rows = [Deal(**item) for item in response.data]
        return rows[:page_size], len(rows) > page_size

    async def list_pending(self) -> list[Deal]:
        response = await self._database.run(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", DealStatus.PENDING.value)
            .not_.is_("buyer_id", "null")
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def expire_unpaid(self, deal_id: int) -> Deal:
        return await self.transition(
            deal_id,
            DealStatus.PENDING,
            status=DealStatus.CANCELLED,
            failure_reason="Payment window expired",
        )

    async def purge_unsuccessful(self, retention_days: int) -> int:
        response = await self._database.rpc(
            "purge_expired_unsuccessful_deals",
            {"p_retention_days": retention_days},
        )
        if isinstance(response.data, list):
            return int(response.data[0]) if response.data else 0
        return int(response.data or 0)

