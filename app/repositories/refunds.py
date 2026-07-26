from datetime import datetime

from app.core.constants import MAX_ERROR_LENGTH
from app.core.enums import RefundStatus
from app.database import SupabaseDatabase
from app.models.entities import Deal, RefundAttempt


class RefundRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def claim(
        self,
        deal: Deal,
        destination: str,
        amount_atomic: int,
        comment: str,
        reason: str,
        reward_destination: str,
        reward_nominal_amount_atomic: int,
        reward_comment: str,
    ) -> RefundAttempt | None:
        response = await self._database.rpc(
            "claim_deal_refund",
            {
                "p_deal_id": deal.id,
                "p_destination": destination,
                "p_amount_atomic": amount_atomic,
                "p_comment": comment,
                "p_reason": reason,
                "p_reward_destination": reward_destination,
                "p_reward_nominal_amount_atomic": reward_nominal_amount_atomic,
                "p_reward_comment": reward_comment,
            },
        )
        return RefundAttempt(**response.data[0]) if response.data else None

    async def save_prepared(
        self,
        attempt_id: int,
        external_message_hash: str,
        signed_boc: str,
        valid_until: datetime,
    ) -> RefundAttempt:
        response = await self._database.rpc(
            "save_prepared_refund",
            {
                "p_attempt_id": attempt_id,
                "p_external_message_hash": external_message_hash,
                "p_signed_boc": signed_boc,
                "p_valid_until": valid_until.isoformat(),
            },
        )
        return RefundAttempt(**response.data[0])

    async def mark_submitted(self, attempt_id: int) -> RefundAttempt:
        return await self._attempt_rpc("mark_refund_submitted", attempt_id)

    async def mark_confirmed(self, attempt_id: int) -> Deal | None:
        response = await self._database.rpc("mark_refund_confirmed", {"p_attempt_id": attempt_id})
        return Deal(**response.data[0]) if response.data else None

    async def mark_bounced(self, attempt_id: int, error: str) -> Deal:
        return await self._error_rpc("mark_refund_bounced", attempt_id, error)

    async def mark_failed(self, attempt_id: int, error: str) -> Deal:
        return await self._error_rpc("mark_refund_failed", attempt_id, error)

    async def list_open(self) -> list[RefundAttempt]:
        response = await self._database.read(
            lambda: self._database.client.table("refund_attempts")
            .select("*")
            .in_(
                "status",
                [
                    RefundStatus.CREATING.value,
                    RefundStatus.PREPARED.value,
                    RefundStatus.SUBMITTED.value,
                ],
            )
            .order("id")
            .execute()
        )
        return [RefundAttempt(**item) for item in response.data]

    async def _attempt_rpc(self, name: str, attempt_id: int) -> RefundAttempt:
        response = await self._database.rpc(name, {"p_attempt_id": attempt_id})
        return RefundAttempt(**response.data[0])

    async def _error_rpc(self, name: str, attempt_id: int, error: str) -> Deal:
        response = await self._database.rpc(
            name,
            {"p_attempt_id": attempt_id, "p_error": error[:MAX_ERROR_LENGTH]},
        )
        return Deal(**response.data[0])
