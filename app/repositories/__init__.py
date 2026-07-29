from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from app.database import SupabaseDatabase
from app.repositories.deals import DealRepository
from app.repositories.disputes import DisputeRepository
from app.repositories.referrals import ReferralRepository
from app.repositories.users import UserRepository
from app.repositories.admin import AdminRepository
from app.repositories.deposits import DepositRepository
from app.repositories.financial_operations import FinancialOperationRepository
from app.repositories.system import SystemSettingsRepository


@dataclass(frozen=True, slots=True)
class Repositories:
    users: UserRepository
    deals: DealRepository
    referrals: ReferralRepository
    disputes: DisputeRepository
    admin: AdminRepository
    deposits: DepositRepository
    financial_operations: FinancialOperationRepository
    system: SystemSettingsRepository

    @classmethod
    def build(cls, database: SupabaseDatabase) -> Self:
        return cls(
            users=UserRepository(database),
            deals=DealRepository(database),
            referrals=ReferralRepository(database),
            disputes=DisputeRepository(database),
            admin=AdminRepository(database),
            deposits=DepositRepository(database),
            financial_operations=FinancialOperationRepository(database),
            system=SystemSettingsRepository(database),
        )


__all__ = [
    "DealRepository",
    "DisputeRepository",
    "ReferralRepository",
    "Repositories",
    "UserRepository",
    "DepositRepository",
    "FinancialOperationRepository",
    "SystemSettingsRepository",
]
