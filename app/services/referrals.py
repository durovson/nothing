from decimal import Decimal

from app.config import Settings
from app.core.constants import TON_DECIMAL_PLACES
from app.core.types import ReferralRepositoryProtocol
from app.models.dto import ReferralStats
from app.models.entities import Deal, User


class ReferralService:
    def __init__(self, settings: Settings, referrals: ReferralRepositoryProtocol):
        self._settings = settings
        self._referrals = referrals

    async def assign_referrer(self, referred_id: int, referrer_id: int) -> bool:
        if referred_id == referrer_id or referrer_id <= 0:
            return False
        return await self._referrals.assign_referrer(referrer_id, referred_id)

    async def get_stats(self, referrer_id: int) -> ReferralStats:
        return await self._referrals.get_stats(referrer_id)

    async def apply_reward(self, seller: User | None, buyer: User | None, deal: Deal) -> None:
        if not seller or not buyer or not seller.referrer_id:
            return
        service_fee = deal.amount * self._settings.ESCROW_FEE_RATE
        reward = (service_fee * self._settings.REFERRAL_FEE_SHARE).quantize(TON_DECIMAL_PLACES)
        if reward > Decimal("0"):
            await self._referrals.add_reward(
                seller.referrer_id,
                seller.telegram_id,
                deal.currency,
                reward,
            )

