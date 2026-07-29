import unittest
from datetime import UTC, datetime
from decimal import Decimal

from app.core.enums import Currency, DealStatus
from app.models.entities import ObservedDeposit
from app.services.usdt_indexer import UsdtDepositIndexer
from tests.helpers import deal, settings


class Deals:
    def __init__(self, item):
        self.item = item

    async def get_by_public_id(self, public_id: str):
        return self.item if public_id == self.item.public_id else None


class Ton:
    guarant_address = "guarant"

    def normalize_address(self, address: str) -> str:
        return address.lower()


def deposit(**changes: object) -> ObservedDeposit:
    values: dict[str, object] = {
        "id": 1, "tx_hash": "tx", "tx_lt": 10, "currency": Currency.USDT,
        "amount_atomic": 1_010_000, "sender": "buyer-snapshot", "memo": "abc123def0",
        "account_address": "guarant", "observed_at": datetime.now(UTC),
    }
    values.update(changes)
    return ObservedDeposit(**values)


class UsdtMatchingTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_asset_amount_memo_and_sender_match(self) -> None:
        target = deal(currency=Currency.USDT, amount=Decimal("1"), status=DealStatus.PENDING)
        indexer = UsdtDepositIndexer(settings(), object(), Deals(target), Ton(), object())
        matched, reason = await indexer._match(deposit())
        self.assertEqual(matched, target)
        self.assertEqual(reason, "matched")

    async def test_wrong_amount_is_unmatched_not_silently_ignored(self) -> None:
        target = deal(currency=Currency.USDT, amount=Decimal("1"), status=DealStatus.PENDING)
        indexer = UsdtDepositIndexer(settings(), object(), Deals(target), Ton(), object())
        matched, reason = await indexer._match(deposit(amount_atomic=1_000_000))
        self.assertIsNone(matched)
        self.assertEqual(reason, "invalid_amount:expected=1010000")

    async def test_unexpected_sender_is_custodial_risk(self) -> None:
        target = deal(currency=Currency.USDT, amount=Decimal("1"), status=DealStatus.PENDING)
        indexer = UsdtDepositIndexer(settings(), object(), Deals(target), Ton(), object())
        matched, reason = await indexer._match(deposit(sender="exchange-hot-wallet"))
        self.assertIsNone(matched)
        self.assertEqual(reason, "unexpected_or_custodial_sender")


if __name__ == "__main__":
    unittest.main()
