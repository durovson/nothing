from __future__ import annotations

from datetime import UTC, datetime

from app.core.enums import UnmatchedPaymentStatus
from app.database import SupabaseDatabase
from app.models.entities import DepositCursor, ObservedDeposit, UnmatchedPayment


class DepositRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def get_cursor(self, scanner: str) -> DepositCursor | None:
        response = await self._database.read(
            lambda: self._database.client.table("deposit_scanner_cursors")
            .select("*").eq("scanner", scanner).limit(1).execute()
        )
        return DepositCursor(**response.data[0]) if response.data else None

    async def save_cursor(
        self, scanner: str, account_address: str, last_lt: int, last_hash: str
    ) -> DepositCursor:
        response = await self._database.run(
            lambda: self._database.client.table("deposit_scanner_cursors").upsert(
                {
                    "scanner": scanner,
                    "account_address": account_address,
                    "last_lt": last_lt,
                    "last_hash": last_hash,
                },
                on_conflict="scanner",
            ).execute()
        )
        return DepositCursor(**response.data[0])

    async def add_observed(self, values: dict[str, object]) -> ObservedDeposit | None:
        response = await self._database.run(
            lambda: self._database.client.table("observed_deposits")
            .upsert(values, on_conflict="tx_hash", ignore_duplicates=True)
            .execute()
        )
        if response.data:
            return ObservedDeposit(**response.data[0])
        tx_hash = str(values["tx_hash"])
        response = await self._database.read(
            lambda: self._database.client.table("observed_deposits")
            .select("*").eq("tx_hash", tx_hash).limit(1).execute()
        )
        return ObservedDeposit(**response.data[0]) if response.data else None

    async def mark_matched(self, deposit_id: int, deal_id: int) -> None:
        await self._database.run(
            lambda: self._database.client.table("observed_deposits")
            .update({
                "matched_deal_id": deal_id,
                "processed_at": datetime.now(UTC).isoformat(),
            })
            .eq("id", deposit_id).execute()
        )

    async def mark_processed(self, deposit_id: int) -> None:
        await self._database.run(
            lambda: self._database.client.table("observed_deposits")
            .update({"processed_at": datetime.now(UTC).isoformat()})
            .eq("id", deposit_id).execute()
        )

    async def mark_desk_checked(self, deposit_id: int) -> None:
        await self._database.run(
            lambda: self._database.client.table("observed_deposits")
            .update({"desk_checked_at": datetime.now(UTC).isoformat()})
            .eq("id", deposit_id).execute(),
            name="deposits:mark-desk-checked",
        )

    async def add_unmatched(
        self, deposit: ObservedDeposit, reason: str
    ) -> UnmatchedPayment | None:
        response = await self._database.run(
            lambda: self._database.client.table("unmatched_payments").upsert(
                {
                    "observed_deposit_id": deposit.id,
                    "tx_hash": deposit.tx_hash,
                    "tx_lt": deposit.tx_lt,
                    "currency": deposit.currency.value,
                    "amount_atomic": deposit.amount_atomic,
                    "sender": deposit.sender,
                    "memo": deposit.memo,
                    "reason": reason,
                },
                on_conflict="observed_deposit_id",
                ignore_duplicates=True,
            ).execute()
        )
        return UnmatchedPayment(**response.data[0]) if response.data else None

    async def list_unmatched(
        self, page: int, page_size: int
    ) -> tuple[list[UnmatchedPayment], bool]:
        offset = max(page, 0) * page_size
        response = await self._database.read(
            lambda: self._database.client.table("unmatched_payments")
            .select("*")
            .eq("status", UnmatchedPaymentStatus.OPEN.value)
            .order("created_at", desc=True)
            .range(offset, offset + page_size)
            .execute()
        )
        rows = [UnmatchedPayment(**row) for row in response.data or []]
        return rows[:page_size], len(rows) > page_size

    async def get_unmatched(self, payment_id: int) -> UnmatchedPayment | None:
        response = await self._database.read(
            lambda: self._database.client.table("unmatched_payments")
            .select("*").eq("id", payment_id).limit(1).execute()
        )
        return UnmatchedPayment(**response.data[0]) if response.data else None
