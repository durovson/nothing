import unittest
from decimal import Decimal

from app.core.constants import REFERRAL_COMMISSION_SHARE
from app.core.enums import Currency
from app.models.entities import User
from app.services.balances import operation_balance_requirement
from app.services.referrals import ReferralService
from tests.helpers import deal, settings


class FinancialEconomicsTests(unittest.TestCase):
    def test_ton_requirement_includes_transfer_and_gas(self) -> None:
        requirement = operation_balance_requirement(settings(), Currency.TON, 1_000_000_000)
        self.assertEqual(requirement.asset_atomic, 0)
        self.assertEqual(requirement.ton_atomic, 1_003_000_000)

    def test_usdt_requirement_checks_asset_and_complete_ton_gas(self) -> None:
        requirement = operation_balance_requirement(settings(), Currency.USDT, 1_000_000)
        self.assertEqual(requirement.asset_atomic, 1_000_000)
        self.assertEqual(requirement.ton_atomic, 53_000_000)

    def test_referral_pool_is_ten_percent_of_service_fee(self) -> None:
        self.assertEqual(REFERRAL_COMMISSION_SHARE, Decimal("0.10"))
        seller = User(telegram_id=100, wallet_address="seller", referrer_id=300)
        service = ReferralService(settings(), object(), object(), object())
        allocations = service.reward_allocations(seller, None, deal())
        self.assertEqual(allocations[0][1], Decimal("0.100000000"))


if __name__ == "__main__":
    unittest.main()
