from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.constants import ADMIN_PAGE_SIZE
from app.core.enums import (
    AdminDisputeAction,
    FinancialAttemptStatus,
    FinancialOperationStatus,
    SystemMode,
)
from app.core.exceptions import DealActionForbiddenError, DealNotFoundError
from app.core.types import (
    AdminRepositoryProtocol,
    DealRepositoryProtocol,
    DepositRepositoryProtocol,
    FinancialOperationRepositoryProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import BotSettings, Deal, DisputeTicket, FinancialOperation, UnmatchedPayment
from app.models.entities import SystemSetting
from app.services.system_mode import SystemModeService


class AdminService:
    def __init__(
        self,
        settings: Settings,
        admin: AdminRepositoryProtocol,
        deals: DealRepositoryProtocol,
        users: UserRepositoryProtocol,
        operations: FinancialOperationRepositoryProtocol,
        deposits: DepositRepositoryProtocol,
        system_mode: SystemModeService,
    ):
        self._settings = settings
        self._admin = admin
        self._deals = deals
        self._users = users
        self._operations = operations
        self._deposits = deposits
        self._system_mode = system_mode
        self._cached_settings: BotSettings | None = None
        self._cache_until = datetime.min.replace(tzinfo=UTC)

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self._settings.admin_ids

    def require_admin(self, telegram_id: int) -> None:
        if not self.is_admin(telegram_id):
            raise DealActionForbiddenError("Administrator access required")

    async def list_disputes(self, actor_id: int, page: int) -> tuple[list[DisputeTicket], bool]:
        self.require_admin(actor_id)
        return await self._admin.list_disputes(max(0, page), ADMIN_PAGE_SIZE)

    async def dispute_card(self, actor_id: int, ticket_id: int) -> tuple[DisputeTicket, Deal]:
        self.require_admin(actor_id)
        ticket = await self._admin.get_dispute(ticket_id)
        if ticket is None:
            raise DealNotFoundError("Dispute ticket not found")
        deal = await self._deals.get(ticket.deal_id)
        if deal is None:
            raise DealNotFoundError("Dispute deal not found")
        return ticket, deal

    async def resolve(
        self,
        actor_id: int,
        ticket_id: int,
        action: AdminDisputeAction,
        reason: str,
    ) -> Deal:
        ticket, _ = await self.dispute_card(actor_id, ticket_id)
        normalized = reason.strip()
        if not 3 <= len(normalized) <= 1000:
            raise ValueError("Resolution reason must contain 3 to 1000 characters")
        if action is AdminDisputeAction.RELEASE:
            deal = await self._admin.resolve_release(ticket.deal_id, normalized)
        elif action is AdminDisputeAction.REFUND:
            deal = await self._admin.resolve_refund(ticket.deal_id, normalized)
        else:
            raise ValueError("Unsupported dispute action")
        if deal is None:
            raise DealActionForbiddenError("The dispute is already resolved")
        return deal

    async def maintenance(self, force: bool = False) -> BotSettings:
        now = datetime.now(UTC)
        if force or self._cached_settings is None or now >= self._cache_until:
            self._cached_settings = await self._admin.get_settings()
            self._cache_until = now + timedelta(seconds=5)
        return self._cached_settings

    async def set_maintenance(self, actor_id: int, enabled: bool, message: str | None = None) -> BotSettings:
        self.require_admin(actor_id)
        self._cached_settings = await self._admin.set_maintenance(enabled, message)
        self._cache_until = datetime.now(UTC) + timedelta(seconds=5)
        return self._cached_settings

    async def system_mode(self, force: bool = False) -> SystemSetting:
        return await self._system_mode.current(force=force)

    async def set_system_mode(
        self, actor_id: int, mode: SystemMode, reason: str
    ) -> SystemSetting:
        self.require_admin(actor_id)
        return await self._system_mode.set_manual(mode, reason, actor_id)

    async def list_user_ids(self, offset: int, limit: int) -> list[int]:
        return await self._users.list_ids(offset, limit)

    async def list_operations(
        self, actor_id: int, page: int
    ) -> tuple[list[FinancialOperation], bool]:
        self.require_admin(actor_id)
        return await self._operations.list_for_admin(max(0, page), ADMIN_PAGE_SIZE)

    async def operation(self, actor_id: int, operation_id: int) -> FinancialOperation:
        self.require_admin(actor_id)
        operation = await self._operations.get(operation_id)
        if operation is None:
            raise DealNotFoundError("Financial operation not found")
        return operation

    async def retry_operation(self, actor_id: int, operation_id: int) -> FinancialOperation:
        current = await self.operation(actor_id, operation_id)
        if current.status not in {
            FinancialOperationStatus.FAILED,
            FinancialOperationStatus.BOUNCED,
        }:
            raise DealActionForbiddenError("Only a proven failed or bounced operation can be retried")
        if current.metadata.get("legacy_batch"):
            raise DealActionForbiddenError(
                "Legacy batch cannot be replayed safely; inspect every output and force-complete or resolve manually"
            )
        attempts = await self._operations.list_attempts(operation_id)
        if any(
            attempt.status in {
                FinancialAttemptStatus.PREPARED,
                FinancialAttemptStatus.SUBMITTED,
                FinancialAttemptStatus.UNKNOWN,
            }
            for attempt in attempts
        ):
            raise DealActionForbiddenError(
                "An unresolved signed attempt exists; verify its trace and use force-complete instead of retry"
            )
        operation = await self._operations.reopen(operation_id, f"admin:{actor_id}")
        if operation is None:
            raise DealActionForbiddenError("Operation cannot be retried")
        return operation

    async def reopen_operation(self, actor_id: int, operation_id: int) -> FinancialOperation:
        current = await self.operation(actor_id, operation_id)
        if current.status is not FinancialOperationStatus.MANUAL_REVIEW:
            raise DealActionForbiddenError("Only a manual-review operation can be reopened")
        if current.metadata.get("legacy_batch"):
            raise DealActionForbiddenError("Legacy batch cannot be reopened safely")
        attempts = await self._operations.list_attempts(operation_id)
        if any(
            attempt.status in {
                FinancialAttemptStatus.PREPARED,
                FinancialAttemptStatus.SUBMITTED,
                FinancialAttemptStatus.UNKNOWN,
            }
            for attempt in attempts
        ):
            raise DealActionForbiddenError(
                "Unresolved attempt exists; verify it and force-complete or keep manual review"
            )
        operation = await self._operations.reopen(operation_id, f"reopened by admin:{actor_id}")
        if operation is None:
            raise DealActionForbiddenError("Operation cannot be reopened")
        return operation

    async def stop_operation(self, actor_id: int, operation_id: int) -> FinancialOperation:
        await self.operation(actor_id, operation_id)
        operation = await self._operations.mark_manual_review(
            operation_id, f"Stopped for manual review by admin:{actor_id}"
        )
        if operation is None:
            raise DealActionForbiddenError("Operation cannot be stopped")
        return operation

    async def force_complete_operation(
        self, actor_id: int, operation_id: int, tx_hash: str, reason: str
    ) -> FinancialOperation:
        await self.operation(actor_id, operation_id)
        normalized_hash = tx_hash.strip().lower()
        normalized_reason = reason.strip()
        if len(normalized_hash) != 64 or any(c not in "0123456789abcdef" for c in normalized_hash):
            raise ValueError("Transaction hash must contain exactly 64 hexadecimal characters")
        if not 3 <= len(normalized_reason) <= 1000:
            raise ValueError("Reason must contain 3 to 1000 characters")
        operation = await self._operations.force_complete(
            operation_id, normalized_hash, f"admin:{actor_id}: {normalized_reason}"
        )
        if operation is None:
            raise DealActionForbiddenError("Operation is already confirmed")
        return operation

    async def list_unmatched(
        self, actor_id: int, page: int
    ) -> tuple[list[UnmatchedPayment], bool]:
        self.require_admin(actor_id)
        return await self._deposits.list_unmatched(max(0, page), ADMIN_PAGE_SIZE)

    async def unmatched(self, actor_id: int, payment_id: int) -> UnmatchedPayment:
        self.require_admin(actor_id)
        payment = await self._deposits.get_unmatched(payment_id)
        if payment is None:
            raise DealNotFoundError("Unmatched payment not found")
        return payment

    async def refund_unmatched(self, actor_id: int, payment_id: int) -> FinancialOperation:
        payment = await self.unmatched(actor_id, payment_id)
        if not payment.sender:
            raise DealActionForbiddenError("Observed sender is missing; automatic refund is unsafe")
        operation = await self._operations.plan_unmatched_refund(payment.id, payment.sender)
        if operation is None:
            raise DealActionForbiddenError("Payment is already resolved")
        return operation
