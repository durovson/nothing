from datetime import datetime

from app.core.constants import MAX_ERROR_LENGTH
from app.core.enums import CollectionStatus
from app.database import SupabaseDatabase
from app.models.entities import CollectionAttempt, Deal


class CollectionRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def claim(
        self,
        deal: Deal,
        destination: str,
        comment: str,
    ) -> CollectionAttempt | None:
        response = await self._database.rpc(
            "claim_deal_collection",
            {
                "p_deal_id": deal.id,
                "p_destination": destination,
                "p_comment": comment,
            },
        )
        return CollectionAttempt(**response.data[0]) if response.data else None

    async def save_prepared(
        self,
        attempt_id: int,
        external_message_hash: str,
        signed_boc: str,
        valid_until: datetime,
    ) -> CollectionAttempt:
        response = await self._database.rpc(
            "save_prepared_collection",
            {
                "p_attempt_id": attempt_id,
                "p_external_message_hash": external_message_hash,
                "p_signed_boc": signed_boc,
                "p_valid_until": valid_until.isoformat(),
            },
        )
        return CollectionAttempt(**response.data[0])

    async def mark_submitted(self, attempt_id: int) -> CollectionAttempt:
        response = await self._database.rpc(
            "mark_collection_submitted",
            {"p_attempt_id": attempt_id},
        )
        return CollectionAttempt(**response.data[0])

    async def mark_confirmed(
        self,
        attempt_id: int,
        delivery_deadline: datetime,
    ) -> Deal | None:
        response = await self._database.rpc(
            "mark_collection_confirmed",
            {
                "p_attempt_id": attempt_id,
                "p_delivery_deadline_at": delivery_deadline.isoformat(),
            },
        )
        return Deal(**response.data[0]) if response.data else None

    async def mark_bounced(self, attempt_id: int, error: str) -> Deal:
        return await self._mark_error("mark_collection_bounced", attempt_id, error)

    async def mark_failed(self, attempt_id: int, error: str) -> Deal:
        return await self._mark_error("mark_collection_failed", attempt_id, error)

    async def list_open(self) -> list[CollectionAttempt]:
        response = await self._database.run(
            lambda: self._database.client.table("collection_attempts")
            .select("*")
            .in_(
                "status",
                [
                    CollectionStatus.CREATING.value,
                    CollectionStatus.PREPARED.value,
                    CollectionStatus.SUBMITTED.value,
                ],
            )
            .order("id")
            .execute()
        )
        return [CollectionAttempt(**item) for item in response.data]

    async def _mark_error(self, rpc: str, attempt_id: int, error: str) -> Deal:
        response = await self._database.rpc(
            rpc,
            {"p_attempt_id": attempt_id, "p_error": error[:MAX_ERROR_LENGTH]},
        )
        return Deal(**response.data[0])
