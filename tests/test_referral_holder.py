from decimal import Decimal
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from app.core.enums import Currency, ReferralLevel
from app.models.dto import ReferralProfile
from app.models.entities import Deal, User
from app.services.referrals import ReferralService


class _ReferralRepository:
    def __init__(self, profile: ReferralProfile):
        self.profile = profile

    async def get_profiles(self, user_ids: set[int]) -> dict[int, ReferralProfile]:
        return {user_id: self.profile.model_copy(update={"user_id": user_id}) for user_id in user_ids}


class ReferralHolderAllocationTests(IsolatedAsyncioTestCase):
    async def _allocation_for(self, profile: ReferralProfile):
        service = ReferralService(
            SimpleNamespace(ESCROW_FEE_RATE=Decimal("0.01")),
            _ReferralRepository(profile),
            SimpleNamespace(),
            SimpleNamespace(),
        )
        seller = User(telegram_id=10, referrer_id=20)
        deal = Deal.model_construct(id=1, amount=Decimal("100"), currency=Currency.TON)
        allocations = await service.reward_allocations(seller, None, deal)
        self.assertEqual(len(allocations), 1)
        return allocations[0]

    async def test_holder_receives_thirty_percent_of_service_fee(self) -> None:
        allocation = await self._allocation_for(
            ReferralProfile(
                user_id=20,
                holder_community_id=7,
                holder_community_name="Collection holders",
                holder_share=Decimal("0.30"),
            )
        )
        self.assertEqual(allocation.amount, Decimal("0.300000000"))
        self.assertEqual(allocation.reward_source, "holder")
        self.assertEqual(allocation.community_id, 7)

    async def test_special_overrides_holder(self) -> None:
        allocation = await self._allocation_for(
            ReferralProfile(
                user_id=20,
                level=ReferralLevel.SPECIAL,
                holder_community_id=7,
                holder_share=Decimal("0.30"),
            )
        )
        self.assertEqual(allocation.amount, Decimal("0.500000000"))
        self.assertEqual(allocation.reward_source, "special")
        self.assertIsNone(allocation.community_id)

