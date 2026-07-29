from __future__ import annotations

from app.core.constants import MAX_ERROR_LENGTH
from app.core.enums import FinancialOperationFlow, FinancialOperationStatus
from app.database import SupabaseDatabase
from app.models.entities import FinancialOperation, FinancialOperationAttempt
from app.ton.models import PreparedPayout


class FinancialOperationRepository:
    """Persistence gateway for independently recoverable transfer legs."""

    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def plan_collection(
        self,
        *,
        deal_id: int,
        destination: str,
        comment: str,
        unmatched_payment_id: int | None = None,
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "plan_deal_collection_operation",
            {
                "p_deal_id": deal_id,
                "p_destination": destination,
                "p_comment": comment,
                "p_unmatched_payment_id": unmatched_payment_id,
            },
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def plan_payout(
        self,
        *,
        deal_id: int,
        seller_destination: str,
        seller_amount_atomic: int,
        seller_comment: str,
        service_destination: str,
        service_amount_atomic: int,
        service_comment: str,
        referral_allocations: list[dict[str, object]],
    ) -> list[FinancialOperation]:
        response = await self._database.rpc(
            "plan_deal_payout_operations",
            {
                "p_deal_id": deal_id,
                "p_seller_destination": seller_destination,
                "p_seller_amount_atomic": seller_amount_atomic,
                "p_seller_comment": seller_comment,
                "p_service_destination": service_destination,
                "p_service_amount_atomic": service_amount_atomic,
                "p_service_comment": service_comment,
                "p_referral_allocations": referral_allocations,
            },
        )
        return [FinancialOperation(**row) for row in response.data or []]

    async def plan_refund(
        self,
        *,
        deal_id: int,
        buyer_destination: str,
        buyer_amount_atomic: int,
        buyer_comment: str,
        service_destination: str,
        service_amount_atomic: int,
        service_comment: str,
    ) -> list[FinancialOperation]:
        response = await self._database.rpc(
            "plan_deal_refund_operations",
            {
                "p_deal_id": deal_id,
                "p_buyer_destination": buyer_destination,
                "p_buyer_amount_atomic": buyer_amount_atomic,
                "p_buyer_comment": buyer_comment,
                "p_service_destination": service_destination,
                "p_service_amount_atomic": service_amount_atomic,
                "p_service_comment": service_comment,
            },
        )
        return [FinancialOperation(**row) for row in response.data or []]

    async def claim_referral_withdrawal(
        self, user_id: int, currency: str, destination: str, comment: str
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "claim_referral_withdrawal_operation",
            {
                "p_user_id": user_id,
                "p_currency": currency,
                "p_destination": destination,
                "p_comment": comment,
            },
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def plan_unmatched_refund(
        self, payment_id: int, destination: str
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "plan_unmatched_refund_operation",
            {
                "p_payment_id": payment_id,
                "p_destination": destination,
                "p_comment": "Недействительный платеж",
            },
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def claim_due(self, flow: FinancialOperationFlow) -> FinancialOperation | None:
        response = await self._database.rpc(
            "claim_due_financial_operation",
            {"p_flow": flow.value, "p_lock_seconds": 120},
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def prepare_attempt(
        self, operation_id: int, prepared: PreparedPayout
    ) -> FinancialOperationAttempt | None:
        response = await self._database.rpc(
            "prepare_financial_operation_attempt",
            {
                "p_operation_id": operation_id,
                "p_external_message_hash": prepared.normalized_hash,
                "p_signed_boc": prepared.signed_boc,
                "p_valid_until": prepared.valid_until.isoformat(),
            },
        )
        return FinancialOperationAttempt(**response.data[0]) if response.data else None

    async def mark_submitted(self, attempt_id: int) -> FinancialOperationAttempt | None:
        response = await self._database.rpc(
            "mark_financial_attempt_submitted", {"p_attempt_id": attempt_id}
        )
        return FinancialOperationAttempt(**response.data[0]) if response.data else None

    async def mark_confirmed(
        self, attempt_id: int, transaction_hash: str
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "mark_financial_operation_confirmed",
            {"p_attempt_id": attempt_id, "p_transaction_hash": transaction_hash},
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def schedule_retry(
        self,
        attempt_id: int,
        error: str,
        *,
        bounced: bool = False,
        uncertain: bool = False,
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "schedule_financial_operation_retry",
            {
                "p_attempt_id": attempt_id,
                "p_error": error[:MAX_ERROR_LENGTH],
                "p_bounced": bounced,
                "p_uncertain": uncertain,
            },
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def schedule_unprepared_retry(
        self, operation_id: int, error: str
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "schedule_unprepared_financial_operation_retry",
            {
                "p_operation_id": operation_id,
                "p_error": error[:MAX_ERROR_LENGTH],
            },
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def get(self, operation_id: int) -> FinancialOperation | None:
        response = await self._database.read(
            lambda: self._database.client.table("financial_operations")
            .select("*")
            .eq("id", operation_id)
            .limit(1)
            .execute()
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def list_attempts(self, operation_id: int) -> list[FinancialOperationAttempt]:
        response = await self._database.read(
            lambda: self._database.client.table("financial_operation_attempts")
            .select("*")
            .eq("operation_id", operation_id)
            .order("attempt_no", desc=True)
            .execute()
        )
        return [FinancialOperationAttempt(**row) for row in response.data or []]

    async def list_submitted(
        self, flow: FinancialOperationFlow
    ) -> list[tuple[FinancialOperation, FinancialOperationAttempt]]:
        operations = await self._list_by_status(
            flow,
            [FinancialOperationStatus.PREPARED, FinancialOperationStatus.SUBMITTED],
        )
        result: list[tuple[FinancialOperation, FinancialOperationAttempt]] = []
        for operation in operations:
            attempts = await self.list_attempts(operation.id)
            active = next(
                (
                    item
                    for item in attempts
                    if item.status.value in {"prepared", "submitted", "unknown"}
                ),
                None,
            )
            if active:
                result.append((operation, active))
        return result

    async def list_for_admin(
        self, page: int, page_size: int
    ) -> tuple[list[FinancialOperation], bool]:
        offset = max(page, 0) * page_size
        response = await self._database.read(
            lambda: self._database.client.table("financial_operations")
            .select("*")
            .in_("status", ["manual_review", "failed", "bounced"])
            .order("updated_at", desc=True)
            .range(offset, offset + page_size)
            .execute()
        )
        rows = [FinancialOperation(**row) for row in response.data or []]
        return rows[:page_size], len(rows) > page_size

    async def reopen(self, operation_id: int, reason: str) -> FinancialOperation | None:
        return await self._admin_rpc("reopen_financial_operation", operation_id, reason)

    async def mark_manual_review(
        self, operation_id: int, reason: str
    ) -> FinancialOperation | None:
        return await self._admin_rpc(
            "mark_financial_operation_manual_review", operation_id, reason
        )

    async def force_complete(
        self, operation_id: int, tx_hash: str, reason: str
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            "force_complete_financial_operation",
            {
                "p_operation_id": operation_id,
                "p_transaction_hash": tx_hash,
                "p_reason": reason[:MAX_ERROR_LENGTH],
            },
        )
        return FinancialOperation(**response.data[0]) if response.data else None

    async def _list_by_status(
        self,
        flow: FinancialOperationFlow,
        statuses: list[FinancialOperationStatus],
    ) -> list[FinancialOperation]:
        response = await self._database.read(
            lambda: self._database.client.table("financial_operations")
            .select("*")
            .eq("flow", flow.value)
            .in_("status", [status.value for status in statuses])
            .order("id")
            .execute()
        )
        return [FinancialOperation(**row) for row in response.data or []]

    async def _admin_rpc(
        self, name: str, operation_id: int, reason: str
    ) -> FinancialOperation | None:
        response = await self._database.rpc(
            name,
            {"p_operation_id": operation_id, "p_reason": reason[:MAX_ERROR_LENGTH]},
        )
        return FinancialOperation(**response.data[0]) if response.data else None
