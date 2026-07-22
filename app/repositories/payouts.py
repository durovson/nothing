from datetime import datetime

from app.core.constants import MAX_ERROR_LENGTH
from app.core.enums import PayoutStatus
from app.database import SupabaseDatabase
from app.models.entities import Deal, PayoutAttempt


class PayoutRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def claim(
        self,
        deal: Deal,
        destination: str,
        amount_atomic: int,
        comment: str,
    ) -> PayoutAttempt | None:
        response = await self._database.rpc(
            "claim_deal_payout",
            {
                "p_deal_id": deal.id,
                "p_destination": destination,
                "p_amount_atomic": amount_atomic,
                "p_comment": comment,
            },
        )
        return PayoutAttempt(**response.data[0]) if response.data else None

    async def save_prepared(
        self,
        attempt_id: int,
        external_message_hash: str,
        signed_boc: str,
        valid_until: datetime,
    ) -> PayoutAttempt:
        response = await self._database.rpc(
            "save_prepared_payout",
            {
                "p_attempt_id": attempt_id,
                "p_external_message_hash": external_message_hash,
                "p_signed_boc": signed_boc,
                "p_valid_until": valid_until.isoformat(),
            },
        )
        return PayoutAttempt(**response.data[0])

    async def mark_submitted(self, attempt_id: int) -> PayoutAttempt:
        return await self._attempt_rpc("mark_payout_submitted", attempt_id)

    async def mark_confirmed(self, attempt_id: int) -> Deal | None:
        response = await self._database.rpc("mark_payout_confirmed", {"p_attempt_id": attempt_id})
        return Deal(**response.data[0]) if response.data else None

    async def mark_bounced(self, attempt_id: int, error: str) -> Deal:
        response = await self._database.rpc(
            "mark_payout_bounced",
            {"p_attempt_id": attempt_id, "p_error": error[:MAX_ERROR_LENGTH]},
        )
        return Deal(**response.data[0])

    async def mark_failed(self, attempt_id: int, error: str) -> Deal:
        response = await self._database.rpc(
            "mark_payout_failed",
            {"p_attempt_id": attempt_id, "p_error": error[:MAX_ERROR_LENGTH]},
        )
        return Deal(**response.data[0])

    async def list_open(self) -> list[PayoutAttempt]:
        response = await self._database.run(
            lambda: self._database.client.table("payout_attempts")
            .select("*")
            .in_("status", [PayoutStatus.PREPARED.value, PayoutStatus.SUBMITTED.value])
            .order("id")
            .execute()
        )
        return [PayoutAttempt(**item) for item in response.data]

    async def _attempt_rpc(self, name: str, attempt_id: int) -> PayoutAttempt:
        response = await self._database.rpc(name, {"p_attempt_id": attempt_id})
        return PayoutAttempt(**response.data[0])

