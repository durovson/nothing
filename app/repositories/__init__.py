from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from app.database import SupabaseDatabase
from app.repositories.deals import DealRepository
from app.repositories.payouts import PayoutRepository
from app.repositories.referrals import ReferralRepository
from app.repositories.users import UserRepository


@dataclass(frozen=True, slots=True)
class Repositories:
    users: UserRepository
    deals: DealRepository
    payouts: PayoutRepository
    referrals: ReferralRepository

    @classmethod
    def build(cls, database: SupabaseDatabase) -> Self:
        return cls(
            users=UserRepository(database),
            deals=DealRepository(database),
            payouts=PayoutRepository(database),
            referrals=ReferralRepository(database),
        )


__all__ = [
    "DealRepository",
    "PayoutRepository",
    "ReferralRepository",
    "Repositories",
    "UserRepository",
]

