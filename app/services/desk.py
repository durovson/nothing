from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.api.telegram_notifier import TelegramNotificationGateway
from app.core.constants import DESK_PAYMENT_TIMEOUT_SECONDS, DESK_PUBLICATION_FEE
from app.core.enums import Currency, DeskKind
from app.core.types import DepositRepositoryProtocol, TonGatewayProtocol
from app.models.dto import CreateDeskListingCommand
from app.models.entities import DeskListing, ObservedDeposit, User
from app.repositories.desk import DeskRepository
from app.ton.amounts import asset_amount_atomic
from app.services.system_mode import SystemModeService

_USERNAME = re.compile(r"^[A-Za-z0-9_]{5,32}$")


class DeskService:
    """Paid-publication business rules, independent of Telegram FSM/UI."""

    def __init__(
        self,
        repository: DeskRepository,
        deposits: DepositRepositoryProtocol,
        ton: TonGatewayProtocol,
        notifications: TelegramNotificationGateway,
        system_mode: SystemModeService | None = None,
    ):
        self._repository = repository
        self._deposits = deposits
        self._ton = ton
        self._notifications = notifications
        self._system_mode = system_mode

    async def create_listing(
        self,
        user: User,
        *,
        kind: DeskKind,
        description: str,
        deal_currency: Currency,
        price: Decimal | None,
        payment_currency: Currency,
    ) -> DeskListing:
        if self._system_mode is not None:
            await self._system_mode.ensure_new_business_allowed()
        username = (user.username or "").strip().lstrip("@").lower()
        if not _USERNAME.fullmatch(username):
            raise ValueError("telegram_username_required")
        now = datetime.now(UTC)
        return await self._repository.create(CreateDeskListingCommand(
            public_id=secrets.token_hex(5),
            owner_id=user.telegram_id,
            owner_username=username,
            owner_language=user.language,
            kind=kind,
            description=description,
            deal_currency=deal_currency,
            price=price,
            payment_currency=payment_currency,
            publication_fee=DESK_PUBLICATION_FEE,
            publication_fee_atomic=asset_amount_atomic(DESK_PUBLICATION_FEE, payment_currency),
            payment_deadline_at=now + timedelta(seconds=DESK_PAYMENT_TIMEOUT_SECONDS),
        ))

    async def try_process_deposit(self, deposit: ObservedDeposit) -> bool:
        """Claim a Desk payment or safely classify/refund a Desk-like transfer."""
        existing = await self._repository.get_by_deposit(deposit.id)
        if existing is not None:
            await self._deposits.mark_processed(deposit.id)
            return True
        memo = (deposit.memo or "").strip().lstrip("@").lower()
        listing = (
            await self._repository.find_waiting_by_username(memo, deposit.currency.value)
            if memo
            else None
        )
        # Sender fallback is limited below the minimum escrow principal. This
        # prevents a normal deal collection reaching the same guarant wallet
        # from being mistaken for an overpaid Desk invoice.
        sender_fallback_limit = asset_amount_atomic(Decimal("1"), deposit.currency)
        if (
            listing is None
            and deposit.sender
            and deposit.amount_atomic < sender_fallback_limit
        ):
            try:
                normalized_sender = self._ton.normalize_address(deposit.sender)
            except Exception:
                normalized_sender = deposit.sender
            listing = await self._repository.find_waiting_by_sender(
                normalized_sender, deposit.currency.value
            )
        if listing is None:
            return False
        if memo and not _USERNAME.fullmatch(memo):
            # The user explicitly supplied a display name/arbitrary text instead
            # of a Telegram username. It cannot be trusted as an identity key and
            # per Desk policy is held for administrator review, not auto-refunded.
            await self._deposits.add_unmatched(
                deposit, "desk_display_name_instead_of_username_manual_review"
            )
            await self._deposits.mark_processed(deposit.id)
            return True
        if not memo:
            await self._repository.plan_invalid_refund(deposit, "desk_missing_memo")
            return True
        if memo != listing.owner_username.lower():
            await self._repository.plan_invalid_refund(
                deposit, "desk_invalid_identity_comment"
            )
            return True
        if deposit.amount_atomic != listing.publication_fee_atomic:
            await self._repository.plan_invalid_refund(deposit, "desk_invalid_publication_amount")
            return True
        claimed = await self._repository.claim_payment(listing.id, deposit)
        if claimed is None:
            await self._repository.plan_invalid_refund(deposit, "desk_invoice_expired_or_already_paid")
            return True
        message_id = await self._notifications.publish_desk_listing(claimed)
        if message_id is None:
            await self._repository.mark_publication_failed(claimed.id, "Telegram Desk publication failed")
            await self._repository.plan_invalid_refund(deposit, "desk_publication_failed")
            return True
        published = await self._repository.mark_published(claimed.id, message_id)
        await self._deposits.mark_processed(deposit.id)
        if published is not None:
            await self._notifications.desk_listing_published(published)
        return True

    async def expire_due(self) -> int:
        return await self._repository.expire_due()

    @property
    def guarant_address(self) -> str:
        return self._ton.guarant_address
