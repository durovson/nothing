import unittest
from datetime import UTC, datetime
from decimal import Decimal

from app.core.enums import Currency, DealStatus, DealType, WalletVersion
from app.models.dto import PaymentObservation
from app.models.entities import Deal
from app.services.ton_indexer import TonDepositIndexer
from tests.helpers import settings


class Ton:
    @staticmethod
    def normalize_address(value: str) -> str:
        return value


class TonMatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.indexer = TonDepositIndexer(
            settings(), object(), object(), Ton(), object(), object()
        )
        self.deal = Deal(
            id=7,
            public_id="d32e9ef40e",
            subwallet_id=7,
            wallet_version=WalletVersion.V5R1,
            creator_id=1,
            buyer_id=2,
            buyer_wallet_snapshot="buyer",
            deal_type=DealType.OFFER,
            description="offer",
            currency=Currency.TON,
            amount=Decimal("1"),
            status=DealStatus.PENDING,
            wallet_address="escrow",
        )

    def observation(
        self, *, amount: int = 1_020_000_000, memo: str = "d32e9ef40e"
    ) -> PaymentObservation:
        return PaymentObservation(
            tx_hash="a" * 64,
            tx_lt=1,
            amount_atomic=amount,
            sender="buyer",
            memo=memo,
            observed_at=datetime.now(UTC),
        )

    def test_exact_ton_payment_matches(self) -> None:
        self.assertEqual(
            self.indexer._mismatch_reason(self.deal, self.observation()), "matched"
        )

    def test_wrong_ton_amount_becomes_unmatched(self) -> None:
        reason = self.indexer._mismatch_reason(
            self.deal, self.observation(amount=1_019_000_000)
        )
        self.assertEqual(reason, "invalid_amount:expected=1020000000")

    def test_wrong_ton_memo_becomes_unmatched(self) -> None:
        self.assertEqual(
            self.indexer._mismatch_reason(self.deal, self.observation(memo="wrong")),
            "missing_or_invalid_memo",
        )
