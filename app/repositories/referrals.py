from decimal import Decimal

from app.core.enums import Currency
from app.database import SupabaseDatabase
from app.models.dto import ReferralStats


class ReferralRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def assign_referrer(self, referrer_id: int, referred_id: int) -> bool:
        response = await self._database.rpc(
            "assign_user_referrer",
            {"p_referrer_id": referrer_id, "p_referred_id": referred_id},
        )
        return bool(response.data)

    async def get_stats(self, referrer_id: int) -> ReferralStats:
        response = await self._database.run(
            lambda: self._database.client.table("referrals")
            .select("*")
            .eq("referrer_id", referrer_id)
            .execute()
        )
        rows = response.data or []
        return ReferralStats(
            count=len(rows),
            earned_ton=sum((Decimal(str(row.get("earned_ton") or 0)) for row in rows), start=Decimal("0")),
            earned_usdt=sum((Decimal(str(row.get("earned_usdt") or 0)) for row in rows), start=Decimal("0")),
        )

    async def add_reward(
        self,
        referrer_id: int,
        referred_id: int,
        currency: Currency,
        amount: Decimal,
    ) -> None:
        await self._database.rpc(
            "credit_referral_reward",
            {
                "p_referrer_id": referrer_id,
                "p_referred_id": referred_id,
                "p_currency": currency.value,
                "p_amount": str(amount),
            },
        )
