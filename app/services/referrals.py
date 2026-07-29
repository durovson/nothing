from __future__ import annotations

from decimal import Decimal

from app.config import Settings
from app.core.constants import (
    REFERRAL_COMMISSION_SHARE,
    REFERRAL_MIN_WITHDRAW_TON,
    REFERRAL_MIN_WITHDRAW_USDT,
    REFERRAL_WITHDRAW_COMMENT,
)
from app.core.enums import Currency, FinancialOperationFlow
from app.core.exceptions import MissingLinkedWalletError, ReferralWithdrawalError, ServiceUnavailableError
from app.core.types import (
    FinancialOperationRepositoryProtocol,
    ReferralRepositoryProtocol,
    TonGatewayProtocol,
)
from app.models.dto import ReferralStats
from app.models.entities import Deal, ReferralWithdrawal, User
from app.ton.amounts import asset_quantum
from app.services.system_mode import SystemModeService


class ReferralService:
    def __init__(
        self,
        settings: Settings,
        referrals: ReferralRepositoryProtocol,
        operations: FinancialOperationRepositoryProtocol,
        ton: TonGatewayProtocol,
        system_mode: SystemModeService | None = None,
    ):
        self._settings = settings
        self._referrals = referrals
        self._operations = operations
        self._ton = ton
        self._system_mode = system_mode

    async def assign_referrer(self, referred_id: int, referrer_id: int) -> bool:
        if referred_id == referrer_id or referrer_id <= 0:
            return False
        return await self._referrals.assign_referrer(referrer_id, referred_id)

    async def get_stats(self, referrer_id: int) -> ReferralStats:
        return await self._referrals.get_stats(referrer_id)

    def reward_allocations(
        self, seller: User | None, buyer: User | None, deal: Deal
    ) -> list[tuple[User, Decimal]]:
        participants = [item for item in (seller, buyer) if item and item.referrer_id]
        if not participants:
            return []
        service_fee = deal.amount * self._settings.ESCROW_FEE_RATE
        pool = (service_fee * REFERRAL_COMMISSION_SHARE).quantize(
            asset_quantum(deal.currency)
        )
        if pool <= 0:
            return []
        share = (pool / len(participants)).quantize(asset_quantum(deal.currency))
        allocations = [(participant, share) for participant in participants]
        remainder = pool - share * len(participants)
        if remainder:
            participant, amount = allocations[0]
            allocations[0] = (participant, amount + remainder)
        return allocations

    def reward_total(
        self, seller: User | None, buyer: User | None, deal: Deal
    ) -> Decimal:
        return sum(
            (amount for _, amount in self.reward_allocations(seller, buyer, deal)),
            start=Decimal("0"),
        )

    async def request_withdrawal(
        self, user: User, currency: Currency
    ) -> ReferralWithdrawal:
        if self._system_mode is not None and not await self._system_mode.allows_flow(FinancialOperationFlow.REFERRAL):
            raise ServiceUnavailableError("В аварийном режиме реферальные выводы приостановлены")
        if not user.wallet_address:
            raise MissingLinkedWalletError("A linked wallet is required for referral withdrawal")
        stats = await self.get_stats(user.telegram_id)
        amount = stats.balance_ton if currency is Currency.TON else stats.balance_usdt
        minimum = (
            REFERRAL_MIN_WITHDRAW_TON
            if currency is Currency.TON
            else REFERRAL_MIN_WITHDRAW_USDT
        )
        if amount < minimum:
            raise ReferralWithdrawalError(f"Minimum withdrawal is {minimum} {currency.value}")
        operation = await self._operations.claim_referral_withdrawal(
            user.telegram_id,
            currency.value,
            self._ton.normalize_address(user.wallet_address),
            REFERRAL_WITHDRAW_COMMENT,
        )
        if operation is None or operation.referral_withdrawal_id is None:
            raise ReferralWithdrawalError("Balance is empty or another withdrawal is active")
        withdrawal = await self._referrals.get_withdrawal(operation.referral_withdrawal_id)
        if withdrawal is None:
            raise ReferralWithdrawalError("Withdrawal ledger was created without a source record")
        return withdrawal
