from __future__ import annotations

import logging
import secrets
from decimal import Decimal
from urllib.parse import urlencode

from app.config import Settings
from app.core.constants import PUBLIC_DEAL_ID_BYTES
from app.core.enums import Currency, DealStatus, DealType
from app.core.exceptions import (
    DealAmountTooSmallError,
    DealNotFoundError,
    MissingLinkedWalletError,
    ChannelConfigurationError,
)
from app.core.types import DealRepositoryProtocol, TonGatewayProtocol, UserRepositoryProtocol
from app.models.dto import CreateDealCommand
from app.models.entities import Deal
from app.ton.amounts import asset_payment_amount, asset_payment_amount_atomic, asset_quantum

logger = logging.getLogger(__name__)


class DealService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        users: UserRepositoryProtocol,
        ton: TonGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._users = users
        self._ton = ton

    async def create_deal(
        self,
        creator_id: int,
        deal_type: DealType,
        description: str,
        currency: Currency,
        amount: Decimal,
        channel_id: int | None = None,
        channel_title: str | None = None,
        channel_username: str | None = None,
    ) -> Deal:
        if deal_type is DealType.CHANNEL and (channel_id is None or not channel_title):
            raise ChannelConfigurationError("Channel deal requires a verified channel")
        if deal_type is not DealType.CHANNEL:
            channel_id = None
            channel_title = None
            channel_username = None
        creator = await self._users.get(creator_id)
        if not creator or not creator.wallet_address:
            raise MissingLinkedWalletError("Seller must link a wallet before creating a deal")
        minimum = self.minimum_deal_amount(currency)
        if amount < minimum:
            raise DealAmountTooSmallError(minimum, currency)
        command = CreateDealCommand(
            public_id=secrets.token_hex(PUBLIC_DEAL_ID_BYTES),
            creator_id=creator_id,
            deal_type=deal_type,
            description=description.strip(),
            currency=currency,
            amount=amount,
            channel_id=channel_id,
            channel_title=channel_title,
            channel_username=channel_username,
        )
        deal = await self._deals.create(command)
        try:
            wallet_address = await self._ton.get_deal_address(deal)
            return await self._deals.activate(deal.id, wallet_address)
        except Exception as exc:
            logger.exception("Failed to derive escrow wallet for deal %s", deal.public_id)
            await self._deals.mark_creation_failed(deal.id, str(exc))
            raise

    async def join_deal(self, public_id: str, buyer_id: int) -> Deal | None:
        buyer = await self._users.get(buyer_id)
        if not buyer or not buyer.wallet_address:
            raise MissingLinkedWalletError("Buyer must link a wallet before joining a deal")
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
        if actor_id not in {deal.creator_id, deal.buyer_id}:
            return deal
        cancelled = await self._deals.request_cancellation(deal_id, actor_id)
        return cancelled or deal

    async def get_deal(self, deal_id: int) -> Deal | None:
        return await self._deals.get(deal_id)

    async def claim_join_notification(self, deal: Deal) -> tuple[User, User, int] | None:
        claimed = await self._deals.claim_join_notification(deal.id)
        if not claimed or not claimed.buyer_id:
            return None
        buyer = await self._users.get(claimed.buyer_id)
        seller = await self._users.get(claimed.creator_id)
        if not buyer or not seller:
            return None
        return buyer, seller, await self._deals.count_as_buyer(buyer.telegram_id)

    async def participants(self, deal: Deal) -> tuple[User | None, User | None]:
        buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
        seller = await self._users.get(deal.creator_id)
        return buyer, seller

    async def list_user_deals(self, telegram_id: int, page: int = 0) -> tuple[list[Deal], int]:
        return await self._deals.list_for_user(
            telegram_id,
            page=max(0, page),
            page_size=min(self._settings.DEALS_PAGE_SIZE, 5),
        )

    def buyer_payment_amount(self, deal: Deal) -> Decimal:
        return asset_payment_amount(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )

    def tonkeeper_payment_link(self, deal: Deal) -> str:
        if not deal.wallet_address:
            raise ValueError("Deal payment address is missing")
        params: dict[str, str] = {
            "amount": str(asset_payment_amount_atomic(
                deal.amount, deal.currency, self._settings.ESCROW_FEE_RATE,
                self._settings.TON_PAYOUT_FEE_RESERVE,
            )),
            "text": deal.public_id,
        }
        if deal.currency is Currency.USDT:
            params["jetton"] = self._settings.USDT_MASTER_ADDRESS
        return f"https://app.tonkeeper.com/transfer/{deal.wallet_address}?{urlencode(params)}"

    def minimum_deal_amount(self, currency: Currency) -> Decimal:
        configured = (
            self._settings.MIN_DEAL_AMOUNT
            if currency is Currency.TON
            else self._settings.MIN_USDT_DEAL_AMOUNT
        )
        return configured.quantize(asset_quantum(currency))

    async def cleanup_retention(self) -> int:
        deleted = await self._deals.purge_unsuccessful(self._settings.FAILED_DEAL_RETENTION_DAYS)
        if deleted:
            logger.info("Deleted %s unsuccessful deals past retention", deleted)
        return deleted
