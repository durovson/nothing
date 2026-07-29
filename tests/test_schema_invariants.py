import unittest
from pathlib import Path


MIGRATION = (
    Path(__file__).parents[1]
    / "app"
    / "database"
    / "migrations"
    / "20260728_financial_ledger.sql"
)


class SchemaInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()

    def test_financial_foreign_keys_are_restrict(self) -> None:
        for table in ("deal_payments", "collection_attempts", "payout_attempts", "refund_attempts"):
            marker = f"alter table public.{table} add constraint"
            section = self.sql[self.sql.index(marker):]
            self.assertIn("on delete restrict", section[:400])

    def test_retention_archives_only_unpaid_nonfinancial_failures(self) -> None:
        start = self.sql.index("function public.archive_expired_unsuccessful_deals")
        section = self.sql[start:start + 1400]
        self.assertIn("status in ('cancelled','creation_failed')", section)
        self.assertIn("paid_tx_hash is null", section)
        self.assertIn("not exists(select 1 from public.deal_payments", section)
        self.assertNotIn("delete from", section)

    def test_retry_schedule_and_manual_review_are_declared(self) -> None:
        for delay in ("1 minute", "5 minutes", "15 minutes", "1 hour", "6 hours", "24 hours"):
            self.assertIn(delay, self.sql)
        self.assertIn("'manual_review'", self.sql)
        self.assertIn("v_retry>=7", self.sql)

    def test_dispute_and_deal_are_resolved_in_one_database_function(self) -> None:
        for name in ("resolve_dispute_release", "resolve_dispute_refund"):
            start = self.sql.index(f"function public.{name}")
            section = self.sql[start:start + 1800]
            self.assertIn("update public.deals", section)
            self.assertIn("update public.dispute_tickets", section)

    def test_cancellation_function_declares_ticket_id(self) -> None:
        start = self.sql.index("function public.request_deal_cancellation")
        section = self.sql[start:start + 2400]
        self.assertIn("v_ticket_id bigint", section)

    def test_collection_uses_the_shared_ledger(self) -> None:
        self.assertIn("'collection_transfer'", self.sql)
        self.assertIn("plan_deal_collection_operation", self.sql)
        self.assertIn("legacy collection requires on-chain reconciliation", self.sql)

    def test_operational_safety_has_one_hour_timeout(self) -> None:
        safety = (MIGRATION.parent / "20260729_operational_safety.sql").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("payment_deadline_at", safety)
        self.assertIn("interval '1 hour'", safety)
        self.assertIn("cancel_expired_pending_deals", safety)

    def test_deadline_race_uses_blockchain_observation_time(self) -> None:
        safety = (MIGRATION.parent / "20260730_worker_and_deadline_safety.sql").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("p_observed_at>v_deadline", safety)
        self.assertIn("v_deal.resolution is distinct from 'timeout'", safety)
        self.assertIn("interval '24 hours'", safety)
        self.assertIn("for update", safety)

    def test_semantic_financial_idempotency_is_enforced(self) -> None:
        safety = (MIGRATION.parent / "20260730_worker_and_deadline_safety.sql").read_text(
            encoding="utf-8"
        ).lower()
        for index in (
            "financial_operations_deal_leg_uidx",
            "financial_operations_referral_withdrawal_uidx",
            "financial_operations_unmatched_leg_uidx",
            "financial_operations_deal_collection_uidx",
        ):
            self.assertIn(index, safety)


if __name__ == "__main__":
    unittest.main()
