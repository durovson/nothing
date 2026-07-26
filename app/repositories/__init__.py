from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from app.database import SupabaseDatabase
from app.repositories.collections import CollectionRepository
from app.repositories.deals import DealRepository
from app.repositories.disputes import DisputeRepository
from app.repositories.payouts import PayoutRepository
from app.repositories.referrals import ReferralRepository
from app.repositories.refunds import RefundRepository
from app.repositories.users import UserRepository
from app.repositories.admin import AdminRepository


@dataclass(frozen=True, slots=True)
class Repositories:
    users: UserRepository
    deals: DealRepository
    payouts: PayoutRepository
    referrals: ReferralRepository
    collections: CollectionRepository
    refunds: RefundRepository
    disputes: DisputeRepository
    admin: AdminRepository

    @classmethod
    def build(cls, database: SupabaseDatabase) -> Self:
        return cls(
            users=UserRepository(database),
            deals=DealRepository(database),
            payouts=PayoutRepository(database),
            referrals=ReferralRepository(database),
            collections=CollectionRepository(database),
            refunds=RefundRepository(database),
            disputes=DisputeRepository(database),
            admin=AdminRepository(database),
        )


__all__ = [
    "DealRepository",
    "CollectionRepository",
    "PayoutRepository",
    "RefundRepository",
    "DisputeRepository",
    "ReferralRepository",
    "Repositories",
    "UserRepository",
]
