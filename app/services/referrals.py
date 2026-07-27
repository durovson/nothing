import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.config import Settings
from app.core.constants import (
    REFERRAL_COMMISSION_SHARE,
    REFERRAL_MIN_WITHDRAW_TON,
    REFERRAL_MIN_WITHDRAW_USDT,
    REFERRAL_WITHDRAW_COMMENT,
)
from app.core.enums import Currency, ReferralWithdrawalStatus, TraceStatus
from app.core.exceptions import MissingLinkedWalletError, ReferralWithdrawalError
from app.ton.amounts import asset_amount_atomic, asset_quantum, payout_amount_atomic
from app.core.types import ReferralRepositoryProtocol, TonGatewayProtocol
from app.models.dto import ReferralStats
from app.models.entities import Deal, ReferralWithdrawal, User
from app.ton.models import PayoutMessage

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(
        self, settings: Settings, referrals: ReferralRepositoryProtocol, ton: TonGatewayProtocol
    ):
        self._settings = settings
        self._referrals = referrals
        self._ton = ton

    async def assign_referrer(self, referred_id: int, referrer_id: int) -> bool:
        if referred_id == referrer_id or referrer_id <= 0:
            return False
        return await self._referrals.assign_referrer(referrer_id, referred_id)

    async def get_stats(self, referrer_id: int) -> ReferralStats:
        return await self._referrals.get_stats(referrer_id)

    async def apply_reward(self, seller: User | None, buyer: User | None, deal: Deal) -> None:
        for participant, reward in self.reward_allocations(seller, buyer, deal):
            if participant.referrer_id:
                await self._referrals.add_reward(
                    deal.id, participant.referrer_id, participant.telegram_id,
                    deal.currency, reward,
                )

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
            first, amount = allocations[0]
            allocations[0] = (first, amount + remainder)
        return allocations

    def reward_total(
        self, seller: User | None, buyer: User | None, deal: Deal
    ) -> Decimal:
        return sum(
            (amount for _, amount in self.reward_allocations(seller, buyer, deal)),
            start=Decimal("0"),
        )

    async def request_withdrawal(self, user: User, currency: Currency) -> ReferralWithdrawal:
        if not user.wallet_address:
            raise MissingLinkedWalletError("A linked wallet is required for referral withdrawal")
        stats = await self.get_stats(user.telegram_id)
        amount = stats.balance_ton if currency is Currency.TON else stats.balance_usdt
        minimum = (
            REFERRAL_MIN_WITHDRAW_TON
            if currency is Currency.TON else REFERRAL_MIN_WITHDRAW_USDT
        )
        if amount < minimum:
            raise ReferralWithdrawalError(f"Minimum withdrawal is {minimum} {currency.value}")
        amount_atomic = asset_amount_atomic(amount, currency)
        if await self._ton.get_guarant_asset_balance_atomic(currency) < amount_atomic:
            raise ReferralWithdrawalError("Guarant asset balance is insufficient")
        gas = payout_amount_atomic(self._settings.TON_GUARANT_PAYOUT_GAS_RESERVE)
        if currency is Currency.USDT:
            gas += payout_amount_atomic(self._settings.USDT_JETTON_TRANSFER_TON)
        if await self._ton.get_guarant_balance_atomic() < gas:
            raise ReferralWithdrawalError("Guarant TON gas reserve is insufficient")
        withdrawal = await self._referrals.claim_withdrawal(
            user.telegram_id, currency, self._ton.normalize_address(user.wallet_address),
            REFERRAL_WITHDRAW_COMMENT,
        )
        if not withdrawal:
            raise ReferralWithdrawalError("Balance is empty or another withdrawal is active")
        await self._prepare_and_broadcast(withdrawal)
        return withdrawal

    async def _prepare_and_broadcast(self, withdrawal: ReferralWithdrawal) -> None:
        try:
            prepared = await self._ton.prepare_guarant_payout([
                PayoutMessage(
                    withdrawal.destination, withdrawal.amount_atomic,
                    withdrawal.comment, currency=withdrawal.currency,
                )
            ])
            withdrawal = await self._referrals.save_prepared_withdrawal(
                withdrawal.id, prepared.normalized_hash, prepared.signed_boc, prepared.valid_until
            )
        except Exception as exc:
            await self._referrals.mark_withdrawal_failed(withdrawal.id, f"prepare: {exc}")
            raise
        try:
            await self._ton.broadcast(withdrawal.signed_boc or "")
        except Exception:
            logger.exception("Referral withdrawal broadcast outcome is uncertain id=%s", withdrawal.id)
            return
        await self._referrals.mark_withdrawal_submitted(withdrawal.id)

    async def reconcile_open(self) -> None:
        for withdrawal in await self._referrals.list_open_withdrawals():
            try:
                await self._reconcile(withdrawal)
            except Exception:
                logger.exception("Referral withdrawal reconciliation failed id=%s", withdrawal.id)

    async def _reconcile(self, withdrawal: ReferralWithdrawal) -> None:
        if withdrawal.status is ReferralWithdrawalStatus.CREATING:
            await self._prepare_and_broadcast(withdrawal)
            return
        if withdrawal.status is ReferralWithdrawalStatus.PREPARED:
            if not withdrawal.signed_boc:
                await self._referrals.mark_withdrawal_failed(withdrawal.id, "Prepared withdrawal has no BOC")
                return
            try:
                await self._ton.broadcast(withdrawal.signed_boc)
            except Exception:
                logger.exception("Referral withdrawal re-broadcast uncertain id=%s", withdrawal.id)
            withdrawal = await self._referrals.mark_withdrawal_submitted(withdrawal.id)
        status = await self._ton.get_referral_withdrawal_trace_status(withdrawal)
        match status:
            case TraceStatus.CONFIRMED:
                await self._referrals.mark_withdrawal_confirmed(withdrawal.id)
            case TraceStatus.BOUNCED:
                await self._referrals.mark_withdrawal_failed(withdrawal.id, "TON transfer bounced", True)
            case TraceStatus.FAILED:
                await self._referrals.mark_withdrawal_failed(withdrawal.id, "TON trace execution failed")
            case TraceStatus.NOT_FOUND | TraceStatus.PENDING:
                if withdrawal.valid_until and datetime.now(UTC) > withdrawal.valid_until + timedelta(
                    seconds=self._settings.TON_TRACE_GRACE_SECONDS
                ):
                    await self._referrals.mark_withdrawal_failed(
                        withdrawal.id, "External message expired and was not found"
                    )
