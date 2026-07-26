from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.constants import ADMIN_PAGE_SIZE
from app.core.enums import AdminDisputeAction
from app.core.exceptions import DealActionForbiddenError, DealNotFoundError
from app.core.types import AdminRepositoryProtocol, DealRepositoryProtocol, UserRepositoryProtocol
from app.models.entities import BotSettings, Deal, DisputeTicket


class AdminService:
    def __init__(
        self,
        settings: Settings,
        admin: AdminRepositoryProtocol,
        deals: DealRepositoryProtocol,
        users: UserRepositoryProtocol,
    ):
        self._settings = settings
        self._admin = admin
        self._deals = deals
        self._users = users
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

    async def list_user_ids(self, offset: int, limit: int) -> list[int]:
        return await self._users.list_ids(offset, limit)
