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
                    "channel_id": command.channel_id,
                    "channel_title": command.channel_title,
                    "channel_username": command.channel_username,
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
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("id", deal_id)
            .limit(1)
            .execute()
        )
        return Deal(**response.data[0]) if response.data else None

    async def get_by_public_id(self, public_id: str) -> Deal | None:
        response = await self._database.read(
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

    async def claim_join_notification(self, deal_id: int) -> Deal | None:
        response = await self._database.rpc(
            "claim_deal_join_notification", {"p_deal_id": deal_id}
        )
        return Deal(**response.data[0]) if response.data else None

    async def count_as_buyer(self, buyer_id: int) -> int:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("id", count="exact")
            .eq("buyer_id", buyer_id)
            .execute()
        )
        return int(response.count or 0)

    async def claim_payment(self, deal_id: int, payment: PaymentObservation) -> Deal | None:
        response = await self._database.rpc(
            "claim_deal_payment",
            {
                "p_deal_id": deal_id,
                "p_tx_hash": payment.tx_hash,
                "p_tx_lt": payment.tx_lt,
                "p_amount_atomic": payment.amount_atomic,
                "p_sender": payment.sender,
                "p_memo_missing": payment.memo is None,
                "p_observed_at": payment.observed_at.isoformat(),
            },
        )
        return Deal(**response.data[0]) if response.data else None

    async def mark_direct_custody(self, deal_id: int, delivery_deadline: datetime) -> Deal | None:
        response = await self._database.rpc(
            "mark_direct_custody_confirmed",
            {"p_deal_id": deal_id, "p_delivery_deadline_at": delivery_deadline.isoformat()},
        )
        return Deal(**response.data[0]) if response.data else None

    async def request_release(self, deal_id: int, buyer_id: int) -> Deal | None:
        response = await self._database.rpc(
            "request_deal_release",
            {"p_deal_id": deal_id, "p_buyer_id": buyer_id},
        )
        return Deal(**response.data[0]) if response.data else None

    async def list_release_requested(self, limit: int = 1) -> list[Deal]:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", DealStatus.RELEASE_REQUESTED.value)
            .order("id")
            .limit(limit)
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def list_collecting(self) -> list[Deal]:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", DealStatus.COLLECTING.value)
            .order("id")
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def mark_delivered(
        self,
        deal_id: int,
        seller_id: int,
        deadline: datetime,
    ) -> Deal | None:
        response = await self._database.rpc(
            "mark_deal_delivered",
            {
                "p_deal_id": deal_id,
                "p_seller_id": seller_id,
                "p_inspection_deadline_at": deadline.isoformat(),
            },
        )
        return Deal(**response.data[0]) if response.data else None

    async def list_delivery_expired(self) -> list[Deal]:
        now = datetime.now(UTC).isoformat()
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", DealStatus.DELIVERY_PENDING.value)
            .neq("deal_type", "channel")
            .lte("delivery_deadline_at", now)
            .order("delivery_deadline_at")
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def list_inspection_expired(self) -> list[Deal]:
        return await self._list_expired(DealStatus.DELIVERED, "inspection_deadline_at")

    async def request_expired_refund(self, deal_id: int) -> Deal | None:
        return await self._deal_rpc("request_expired_delivery_refund", deal_id)

    async def request_auto_release(self, deal_id: int) -> Deal | None:
        return await self._deal_rpc("request_expired_inspection_release", deal_id)

    async def list_refund_requested(self, limit: int = 1) -> list[Deal]:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", DealStatus.REFUND_REQUESTED.value)
            .order("id")
            .limit(limit)
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def list_refund_awaiting_wallet(self) -> list[Deal]:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", DealStatus.REFUND_AWAITING_WALLET.value)
            .order("id")
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def activate_refund_after_wallet(self, deal_id: int) -> Deal | None:
        return await self._deal_rpc("activate_refund_after_wallet", deal_id)

    async def _list_expired(self, status: DealStatus, column: str) -> list[Deal]:
        now = datetime.now(UTC).isoformat()
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("status", status.value)
            .lte(column, now)
            .order(column)
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def _deal_rpc(self, name: str, deal_id: int) -> Deal | None:
        response = await self._database.rpc(name, {"p_deal_id": deal_id})
        return Deal(**response.data[0]) if response.data else None

    async def list_for_user(
        self,
        telegram_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[Deal], int]:
        offset = page * page_size
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*", count="exact")
            .or_(f"creator_id.eq.{telegram_id},buyer_id.eq.{telegram_id}")
            .order("id", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = [Deal(**item) for item in response.data]
        total = int(response.count or 0)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return rows, total_pages

    async def list_pending(self) -> list[Deal]:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .in_("status", [DealStatus.PENDING.value, DealStatus.CANCELLED.value])
            .not_.is_("buyer_id", "null")
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def request_cancellation(self, deal_id: int, actor_id: int) -> Deal | None:
        response = await self._database.rpc(
            "request_deal_cancellation",
            {"p_deal_id": deal_id, "p_actor_id": actor_id},
        )
        return Deal(**response.data[0]) if response.data else None

    async def purge_unsuccessful(self, retention_days: int) -> int:
        response = await self._database.rpc(
            "purge_expired_unsuccessful_deals",
            {"p_retention_days": retention_days},
        )
        if isinstance(response.data, list):
            return int(response.data[0]) if response.data else 0
        return int(response.data or 0)

    async def list_channel_transfer_pending(self) -> list[Deal]:
        response = await self._database.read(
            lambda: self._database.client.table("deals")
            .select("*")
            .eq("deal_type", "channel")
            .eq("status", DealStatus.DELIVERY_PENDING.value)
            .is_("channel_owner_verified_at", "null")
            .not_.is_("buyer_id", "null")
            .order("id")
            .execute()
        )
        return [Deal(**item) for item in response.data]

    async def confirm_channel_owner(self, deal_id: int) -> Deal | None:
        response = await self._database.rpc(
            "confirm_channel_owner_transfer", {"p_deal_id": deal_id}
        )
        return Deal(**response.data[0]) if response.data else None

    async def record_channel_observation(
        self, deal_id: int, member_status: str, error: str | None = None
    ) -> None:
        await self._database.run(
            lambda: self._database.client.table("deals").update({
                "channel_last_member_status": member_status,
                "channel_last_checked_at": datetime.now(UTC).isoformat(),
                "channel_access_error": error[:1000] if error else None,
            }).eq("id", deal_id).eq("deal_type", "channel").execute()
        )

    async def dispute_channel_transfer(self, deal_id: int, reason: str) -> Deal | None:
        response = await self._database.rpc(
            "dispute_expired_channel_transfer",
            {"p_deal_id": deal_id, "p_reason": reason[:1000]},
        )
        return Deal(**response.data[0]) if response.data else None
