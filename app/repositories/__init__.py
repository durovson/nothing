from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from app.database import SupabaseDatabase
from app.repositories.collections import CollectionRepository
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
    collections: CollectionRepository

    @classmethod
    def build(cls, database: SupabaseDatabase) -> Self:
        return cls(
            users=UserRepository(database),
            deals=DealRepository(database),
            payouts=PayoutRepository(database),
            referrals=ReferralRepository(database),
            collections=CollectionRepository(database),
        )


__all__ = [
    "DealRepository",
    "CollectionRepository",
    "PayoutRepository",
    "ReferralRepository",
    "Repositories",
    "UserRepository",
]
