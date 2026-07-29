import unittest
from decimal import Decimal

from app.core.enums import Currency
from app.models.entities import User
from app.services.payouts import PayoutService
from app.services.referrals import ReferralService
from app.services.refunds import RefundService
from tests.helpers import deal, settings


class Users:
    async def get(self, user_id: int):
        if user_id == 100:
            return User(telegram_id=100, wallet_address="changed-seller", referrer_id=300)
        if user_id == 200:
            return User(telegram_id=200, wallet_address="changed-buyer")
        return None


class Ton:
    def normalize_address(self, address: str) -> str:
        return address


class Operations:
    def __init__(self):
        self.payout: dict[str, object] | None = None
        self.refund: dict[str, object] | None = None

    async def plan_payout(self, **values: object):
        self.payout = values
        return []

    async def plan_refund(self, **values: object):
        self.refund = values
        return []


class FinancialPlanningTests(unittest.IsolatedAsyncioTestCase):
    async def test_payout_plans_independent_seller_and_net_service_legs(self) -> None:
        operations = Operations()
        referrals = ReferralService(settings(), object(), object(), Ton())
        service = PayoutService(settings(), object(), operations, Users(), referrals, Ton(), object())
        await service.start_payout(deal())
        assert operations.payout is not None
        self.assertEqual(operations.payout["seller_destination"], "seller-snapshot")
        self.assertEqual(operations.payout["seller_amount_atomic"], 100_000_000_000)
        self.assertEqual(operations.payout["service_amount_atomic"], 900_000_000)
        self.assertEqual(operations.payout["referral_allocations"][0]["amount"], "0.100000000")

    async def test_refund_uses_immutable_buyer_snapshot(self) -> None:
        operations = Operations()
        service = RefundService(settings(), object(), operations, Users(), Ton(), object())
        await service.start_refund(deal(currency=Currency.USDT, amount=Decimal("10")))
        assert operations.refund is not None
        self.assertEqual(operations.refund["buyer_destination"], "buyer-snapshot")
        self.assertEqual(operations.refund["buyer_amount_atomic"], 10_000_000)


if __name__ == "__main__":
    unittest.main()
