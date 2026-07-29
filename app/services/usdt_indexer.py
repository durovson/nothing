from __future__ import annotations

from app.config import Settings
from app.core.enums import Currency, DealStatus
from app.core.types import (
    DealRepositoryProtocol,
    DepositRepositoryProtocol,
    TonGatewayProtocol,
)
from app.models.dto import PaymentObservation
from app.models.entities import Deal, ObservedDeposit
from app.services.collections import CollectionService
from app.ton.amounts import asset_payment_amount_atomic
from app.services.system_mode import SystemModeService

SCANNER_NAME = "guarant-usdt-tep74-v1"


class UsdtDepositIndexer:
    def __init__(
        self,
        settings: Settings,
        deposits: DepositRepositoryProtocol,
        deals: DealRepositoryProtocol,
        ton: TonGatewayProtocol,
        collections: CollectionService,
        system_mode: SystemModeService | None = None,
    ):
        self._settings = settings
        self._deposits = deposits
        self._deals = deals
        self._ton = ton
        self._collections = collections
        self._system_mode = system_mode

    async def run_once(self) -> None:
        if self._system_mode is not None and not await self._system_mode.accepts_deposits():
            return
        cursor = await self._deposits.get_cursor(SCANNER_NAME)
        batch = await self._ton.scan_usdt_deposits(
            cursor.last_lt if cursor else None,
            cursor.last_hash if cursor else None,
        )
        for observation in batch.deposits:
            await self._process(observation)
        if batch.newest_lt is not None and batch.newest_hash:
            await self._deposits.save_cursor(
                SCANNER_NAME,
                self._ton.guarant_address,
                batch.newest_lt,
                batch.newest_hash,
            )

    async def _process(self, observation: PaymentObservation) -> None:
        deposit = await self._deposits.add_observed(
            {
                "tx_hash": observation.tx_hash,
                "tx_lt": observation.tx_lt,
                "currency": Currency.USDT.value,
                "amount_atomic": observation.amount_atomic,
                "sender": observation.sender,
                "memo": observation.memo,
                "account_address": self._ton.guarant_address,
                "jetton_master_address": self._settings.USDT_MASTER_ADDRESS,
                "jetton_wallet_address": observation.jetton_wallet_address,
                "observed_at": observation.observed_at.isoformat(),
            }
        )
        if deposit is None or deposit.processed_at is not None:
            return
        deal, reason = await self._match(deposit)
        if deal is None:
            await self._deposits.add_unmatched(deposit, reason)
            await self._deposits.mark_processed(deposit.id)
            return
        claimed = await self._deals.claim_payment(deal.id, observation)
        if claimed is None:
            await self._deposits.add_unmatched(
                deposit, "deposit_already_claimed_or_deal_changed"
            )
            await self._deposits.mark_processed(deposit.id)
            return
        await self._deposits.mark_matched(deposit.id, deal.id)
        await self._collections.start_collection(claimed)

    async def _match(self, deposit: ObservedDeposit) -> tuple[Deal | None, str]:
        if not deposit.memo:
            return None, "missing_or_malformed_memo"
        deal = await self._deals.get_by_public_id(deposit.memo)
        if deal is None:
            return None, "unknown_memo"
        if deal.currency is not Currency.USDT:
            return None, "memo_belongs_to_different_asset"
        if deal.status not in {DealStatus.PENDING, DealStatus.CANCELLED} or deal.buyer_id is None:
            return None, "deal_is_not_awaiting_payment"
        expected = asset_payment_amount_atomic(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )
        if deposit.amount_atomic != expected:
            return None, f"invalid_amount:expected={expected}"
        buyer_snapshot = deal.buyer_wallet_snapshot or deal.buyer_wallet_address
        if buyer_snapshot:
            if not deposit.sender:
                return None, "missing_sender"
            if self._ton.normalize_address(deposit.sender) != self._ton.normalize_address(
                buyer_snapshot
            ):
                return None, "unexpected_or_custodial_sender"
        return deal, "matched"
