from __future__ import annotations

import logging
import secrets
from decimal import Decimal

from app.config import Settings
from app.core.constants import PUBLIC_DEAL_ID_BYTES
from app.core.enums import Currency, DealStatus, DealType
from app.core.exceptions import DealNotFoundError, UnsupportedCurrencyError
from app.core.types import DealRepositoryProtocol, TonGatewayProtocol
from app.models.dto import CreateDealCommand
from app.models.entities import Deal
from app.ton.amounts import payment_amount

logger = logging.getLogger(__name__)


class DealService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        ton: TonGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._ton = ton

    async def create_deal(
        self,
        creator_id: int,
        deal_type: DealType,
        description: str,
        currency: Currency,
        amount: Decimal,
    ) -> Deal:
        if currency is not Currency.TON:
            raise UnsupportedCurrencyError(
                "USDT_TON is disabled until the jetton payment path is configured"
            )
        command = CreateDealCommand(
            public_id=secrets.token_hex(PUBLIC_DEAL_ID_BYTES),
            creator_id=creator_id,
            deal_type=deal_type,
            description=description.strip(),
            currency=currency,
            amount=amount,
        )
        deal = await self._deals.create(command)
        try:
            wallet_address = await self._ton.get_deal_address(deal.subwallet_id)
            return await self._deals.activate(deal.id, wallet_address)
        except Exception as exc:
            logger.exception("Failed to derive escrow wallet for deal %s", deal.public_id)
            await self._deals.mark_creation_failed(deal.id, str(exc))
            raise

    async def join_deal(self, public_id: str, buyer_id: int) -> Deal | None:
        deal = await self._deals.get_by_public_id(public_id)
        if not deal or deal.creator_id == buyer_id:
            return None
        if deal.buyer_id is not None:
            return deal if deal.buyer_id == buyer_id else None
        if deal.status is not DealStatus.PENDING:
            return None
        claimed = await self._deals.join(public_id, buyer_id)
        if claimed and claimed.buyer_id == buyer_id:
            return claimed
        current = await self._deals.get_by_public_id(public_id)
        return current if current and current.buyer_id == buyer_id else None

    async def cancel_deal(self, deal_id: int, actor_id: int) -> Deal:
        deal = await self._deals.get(deal_id)
        if not deal:
            raise DealNotFoundError(f"Deal {deal_id} not found")
        if deal.creator_id != actor_id or deal.status is not DealStatus.PENDING:
            return deal
        return await self._deals.transition(
            deal_id,
            DealStatus.PENDING,
            status=DealStatus.CANCELLED,
        )

    async def get_deal(self, deal_id: int) -> Deal | None:
        return await self._deals.get(deal_id)

    async def list_user_deals(self, telegram_id: int, page: int = 0) -> tuple[list[Deal], bool]:
        return await self._deals.list_for_user(
            telegram_id,
            page=max(0, page),
            page_size=self._settings.DEALS_PAGE_SIZE,
        )

    def buyer_payment_amount(self, deal: Deal) -> Decimal:
        return payment_amount(deal.amount, self._settings.ESCROW_FEE_RATE)

    async def cleanup_retention(self) -> int:
        deleted = await self._deals.purge_unsuccessful(self._settings.FAILED_DEAL_RETENTION_DAYS)
        if deleted:
            logger.info("Deleted %s unsuccessful deals past retention", deleted)
        return deleted

