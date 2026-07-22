from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import Currency, DealType


class CreateDealCommand(BaseModel):
    public_id: str = Field(min_length=10, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    creator_id: int
    deal_type: DealType
    description: str = Field(min_length=1, max_length=2_000)
    currency: Currency
    amount: Decimal = Field(gt=Decimal("0"))


class PaymentObservation(BaseModel):
    tx_hash: str
    tx_lt: int
    amount_atomic: int
    sender: str | None = None
    memo: str
    observed_at: datetime


class ReferralStats(BaseModel):
    count: int = 0
    earned_ton: Decimal = Decimal("0")
    earned_usdt: Decimal = Decimal("0")

