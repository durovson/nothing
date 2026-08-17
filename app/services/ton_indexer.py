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


class TonDepositIndexer:
    """Cursor-based TON indexer that persists exact and invalid deposits."""

    def __init__(
        self,
        settings: Settings,
        deposits: DepositRepositoryProtocol,
        deals: DealRepositoryProtocol,
        ton: TonGatewayProtocol,
        collections: CollectionService,
        system_mode: SystemModeService,
    ):
        self._settings = settings
        self._deposits = deposits
        self._deals = deals
        self._ton = ton
        self._collections = collections
        self._system_mode = system_mode

    async def run_once(self) -> None:
        if not await self._system_mode.accepts_deposits():
            return
        for deal in await self._deals.list_pending():
            if deal.currency is Currency.TON:
                await self._scan_deal(deal)

    async def _scan_deal(self, deal: Deal) -> None:
        scanner = f"deal-ton-v1:{deal.id}"
        cursor = await self._deposits.get_cursor(scanner)
        batch = await self._ton.scan_ton_deposits(
            deal,
            cursor.last_lt if cursor else None,
            cursor.last_hash if cursor else None,
        )
        staged: list[tuple[PaymentObservation, ObservedDeposit]] = []
        for observation in batch.deposits:
            deposit = await self._deposits.add_observed(
                {
                    "tx_hash": observation.tx_hash,
                    "tx_lt": observation.tx_lt,
                    "currency": Currency.TON.value,
                    "amount_atomic": observation.amount_atomic,
                    "sender": observation.sender,
                    "memo": observation.memo,
                    "account_address": deal.wallet_address,
                    "observed_at": observation.observed_at.isoformat(),
                }
            )
            if deposit and deposit.processed_at is None:
                staged.append((observation, deposit))

        matched_index = next(
            (index for index, (item, _) in enumerate(staged) if self._matches(deal, item)),
            None,
        )
        custody_planned = False
        if matched_index is not None:
            observation, deposit = staged.pop(matched_index)
            claimed = await self._deals.claim_payment(deal.id, observation)
            if claimed:
                await self._deposits.mark_matched(deposit.id, deal.id)
                await self._collections.start_collection(claimed)
                custody_planned = True
            else:
                await self._record_unmatched(deposit, "deposit_already_claimed_or_deal_changed")

        first_unmatched_id: int | None = None
        for observation, deposit in staged:
            reason = self._mismatch_reason(deal, observation)
            unmatched = await self._record_unmatched(deposit, reason)
            if unmatched and first_unmatched_id is None:
                first_unmatched_id = unmatched.id
        if first_unmatched_id is not None and not custody_planned:
            await self._collections.start_unmatched_collection(deal, first_unmatched_id)

        if batch.newest_lt is not None and batch.newest_hash and deal.wallet_address:
            await self._deposits.save_cursor(
                scanner, deal.wallet_address, batch.newest_lt, batch.newest_hash
            )

    async def _record_unmatched(
        self, deposit: ObservedDeposit, reason: str
    ):
        unmatched = await self._deposits.add_unmatched(deposit, reason)
        await self._deposits.mark_processed(deposit.id)
        return unmatched

    def _matches(self, deal: Deal, item: PaymentObservation) -> bool:
        return self._mismatch_reason(deal, item) == "matched"

    def _mismatch_reason(self, deal: Deal, item: PaymentObservation) -> str:
        expected = asset_payment_amount_atomic(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )
        if item.amount_atomic != expected:
            return f"invalid_amount:expected={expected}"
        buyer = deal.buyer_wallet_snapshot or deal.buyer_wallet_address
        if buyer:
            if not item.sender:
                return "missing_sender"
            if self._ton.normalize_address(item.sender) != self._ton.normalize_address(buyer):
                return "unexpected_or_custodial_sender"
        if deal.status not in {DealStatus.PENDING, DealStatus.CANCELLED}:
            return "deal_is_not_awaiting_payment"
        return "matched"
