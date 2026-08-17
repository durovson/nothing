import asyncio
from decimal import Decimal

from app.core.enums import Currency, ReferralWithdrawalStatus
from app.database import SupabaseDatabase
from app.models.dto import ReferralProfile, ReferralStats
from app.models.entities import ReferralWithdrawal


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
        relations, balances, profiles = await asyncio.gather(
            self._database.read(
                lambda: self._database.client.table("referrals")
                .select("id")
                .eq("referrer_id", referrer_id)
                .execute()
            ),
            self._database.read(
                lambda: self._database.client.table("referral_balances")
                .select("currency,balance")
                .eq("user_id", referrer_id)
                .execute()
            ),
            self._database.read(
                lambda: self._database.client.table("referral_profiles")
                .select("user_id,level,ton_volume")
                .eq("user_id", referrer_id)
                .limit(1)
                .execute()
            ),
        )
        values = {str(row["currency"]): Decimal(str(row["balance"])) for row in balances.data or []}
        profile = (
            ReferralProfile(**profiles.data[0])
            if profiles.data
            else ReferralProfile(user_id=referrer_id)
        )
        return ReferralStats(
            count=len(relations.data or []),
            balance_ton=values.get(Currency.TON.value, Decimal(0)),
            balance_usdt=values.get(Currency.USDT.value, Decimal(0)),
            level=profile.level,
            ton_volume=profile.ton_volume,
            commission_share=profile.commission_share,
        )

    async def get_profiles(self, user_ids: set[int]) -> dict[int, ReferralProfile]:
        if not user_ids:
            return {}
        response = await self._database.read(
            lambda: self._database.client.table("referral_profiles")
            .select("user_id,level,ton_volume")
            .in_("user_id", sorted(user_ids))
            .execute()
        )
        profiles = {
            int(row["user_id"]): ReferralProfile(**row)
            for row in response.data or []
        }
        for user_id in user_ids:
            profiles.setdefault(user_id, ReferralProfile(user_id=user_id))
        return profiles

    async def add_reward(
        self,
        deal_id: int,
        referrer_id: int,
        referred_id: int,
        currency: Currency,
        amount: Decimal,
    ) -> bool:
        response = await self._database.rpc(
            "credit_referral_reward",
            {
                "p_deal_id": deal_id,
                "p_referrer_id": referrer_id,
                "p_referred_id": referred_id,
                "p_currency": currency.value,
                "p_amount": str(amount),
            },
        )
        return bool(response.data)

    async def claim_withdrawal(
        self, user_id: int, currency: Currency, destination: str, comment: str
    ) -> ReferralWithdrawal | None:
        response = await self._database.rpc("claim_referral_withdrawal", {
            "p_user_id": user_id, "p_currency": currency.value,
            "p_destination": destination, "p_comment": comment,
        })
        return ReferralWithdrawal(**response.data[0]) if response.data else None

    async def save_prepared_withdrawal(
        self, withdrawal_id: int, external_message_hash: str, signed_boc: str, valid_until,
    ) -> ReferralWithdrawal:
        response = await self._database.rpc("save_prepared_referral_withdrawal", {
            "p_withdrawal_id": withdrawal_id, "p_external_message_hash": external_message_hash,
            "p_signed_boc": signed_boc, "p_valid_until": valid_until.isoformat(),
        })
        return ReferralWithdrawal(**response.data[0])

    async def mark_withdrawal_submitted(self, withdrawal_id: int) -> ReferralWithdrawal:
        response = await self._database.rpc("mark_referral_withdrawal_submitted", {"p_withdrawal_id": withdrawal_id})
        return ReferralWithdrawal(**response.data[0])

    async def mark_withdrawal_confirmed(self, withdrawal_id: int) -> ReferralWithdrawal | None:
        response = await self._database.rpc("mark_referral_withdrawal_confirmed", {"p_withdrawal_id": withdrawal_id})
        return ReferralWithdrawal(**response.data[0]) if response.data else None

    async def mark_withdrawal_failed(
        self, withdrawal_id: int, error: str, bounced: bool = False,
    ) -> ReferralWithdrawal | None:
        response = await self._database.rpc("fail_referral_withdrawal", {
            "p_withdrawal_id": withdrawal_id, "p_error": error[:1000], "p_bounced": bounced,
        })
        return ReferralWithdrawal(**response.data[0]) if response.data else None

    async def list_open_withdrawals(self) -> list[ReferralWithdrawal]:
        response = await self._database.read(
            lambda: self._database.client.table("referral_withdrawals").select("*").in_(
                "status", [ReferralWithdrawalStatus.CREATING.value, ReferralWithdrawalStatus.PREPARED.value, ReferralWithdrawalStatus.SUBMITTED.value]
            ).order("id").execute()
        )
        return [ReferralWithdrawal(**row) for row in response.data or []]

    async def get_withdrawal(self, withdrawal_id: int) -> ReferralWithdrawal | None:
        response = await self._database.read(
            lambda: self._database.client.table("referral_withdrawals")
            .select("*").eq("id", withdrawal_id).limit(1).execute()
        )
        return ReferralWithdrawal(**response.data[0]) if response.data else None
