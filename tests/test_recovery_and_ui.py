import unittest
from datetime import UTC, datetime, timedelta

from app.core.enums import (
    Currency,
    FinancialAttemptStatus,
    FinancialOperationFlow,
    FinancialOperationStatus,
    FinancialOperationType,
    Language,
    TraceStatus,
)
from app.keyboards.deals import deal_actions
from app.locales import TextKey, translate
from app.models.entities import FinancialOperation, FinancialOperationAttempt
from app.services.financial_processor import FinancialOperationProcessor
from app.ton.models import TraceResult
from tests.helpers import deal, settings


def operation(status: FinancialOperationStatus) -> FinancialOperation:
    return FinancialOperation(
        id=10, operation_id="00000000-0000-0000-0000-000000000010",
        idempotency_key="deal:1:payout:seller", flow=FinancialOperationFlow.PAYOUT,
        type=FinancialOperationType.SELLER_TRANSFER, status=status,
        currency=Currency.TON, amount_atomic=1_000_000_000,
        destination="destination", comment="Payment",
    )


def attempt(status: FinancialAttemptStatus, valid_until: datetime) -> FinancialOperationAttempt:
    return FinancialOperationAttempt(
        id=20, operation_id=10, attempt_no=1, status=status,
        external_message_hash="hash", signed_boc="signed-boc", valid_until=valid_until,
    )


class Repository:
    def __init__(self, item, trace_attempt):
        self.item = item
        self.trace_attempt = trace_attempt
        self.submitted: list[int] = []
        self.retries: list[dict[str, object]] = []

    async def list_submitted(self, _flow):
        return [(self.item, self.trace_attempt)]

    async def claim_due(self, _flow):
        return None

    async def mark_submitted(self, attempt_id):
        self.submitted.append(attempt_id)

    async def schedule_retry(self, attempt_id, error, **flags):
        self.retries.append({"id": attempt_id, "error": error, **flags})


class Ton:
    def __init__(self):
        self.broadcasts: list[str] = []

    async def get_financial_operation_trace_status(self, _operation, _attempt):
        return TraceResult(TraceStatus.NOT_FOUND)

    async def broadcast(self, boc: str):
        self.broadcasts.append(boc)


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def test_reviews_link_targets_grnthub_topic_four(self) -> None:
        expected = '<a href="https://t.me/grnthub/4">@grnthub</a>'
        self.assertIn(expected, translate(Language.RU, TextKey.MAIN_MENU_CAPTION))
        self.assertIn(expected, translate(Language.EN, TextKey.MAIN_MENU_CAPTION))

    async def test_prepared_crash_reuses_same_signed_boc(self) -> None:
        repo = Repository(operation(FinancialOperationStatus.PREPARED), attempt(FinancialAttemptStatus.PREPARED, datetime.now(UTC) + timedelta(minutes=1)))
        ton = Ton()
        processor = FinancialOperationProcessor(settings(), FinancialOperationFlow.PAYOUT, repo, ton)
        await processor.run_once()
        self.assertEqual(ton.broadcasts, ["signed-boc"])
        self.assertEqual(repo.submitted, [20])
        self.assertEqual(repo.retries, [])

    async def test_expired_uncertain_transfer_is_never_rebroadcast(self) -> None:
        repo = Repository(operation(FinancialOperationStatus.SUBMITTED), attempt(FinancialAttemptStatus.SUBMITTED, datetime.now(UTC) - timedelta(minutes=10)))
        ton = Ton()
        processor = FinancialOperationProcessor(settings(), FinancialOperationFlow.PAYOUT, repo, ton)
        await processor.run_once()
        self.assertEqual(ton.broadcasts, [])
        self.assertTrue(repo.retries[0]["uncertain"])

    def test_cancel_button_disappears_after_payment(self) -> None:
        pending = deal(status="pending")
        paid = deal(status="delivery_pending")
        pending_data = [button.callback_data for row in deal_actions(Language.RU, pending, 200).inline_keyboard for button in row]
        paid_data = [button.callback_data for row in deal_actions(Language.RU, paid, 200).inline_keyboard for button in row]
        self.assertTrue(any(data and ":cancel:" in data for data in pending_data))
        self.assertFalse(any(data and ":cancel:" in data for data in paid_data))


if __name__ == "__main__":
    unittest.main()
