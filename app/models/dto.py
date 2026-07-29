from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import Currency, DealType


class CreateDealCommand(BaseModel):
    public_id: str = Field(min_length=10, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    creator_id: int
    seller_wallet_address: str
    deal_type: DealType
    description: str = Field(min_length=1, max_length=2_000)
    currency: Currency
    amount: Decimal = Field(gt=Decimal("0"))
    channel_id: int | None = None
    channel_title: str | None = Field(default=None, max_length=255)
    channel_username: str | None = Field(default=None, max_length=64)


class ChannelDescriptor(BaseModel):
    channel_id: int
    title: str = Field(min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=64)


class PaymentObservation(BaseModel):
    tx_hash: str
    tx_lt: int
    amount_atomic: int
    sender: str | None = None
    memo: str | None = None
    jetton_wallet_address: str | None = None
    observed_at: datetime


class DepositScanBatch(BaseModel):
    deposits: list[PaymentObservation]
    newest_lt: int | None = None
    newest_hash: str | None = None


class ReferralStats(BaseModel):
    count: int = 0
    balance_ton: Decimal = Decimal("0")
    balance_usdt: Decimal = Decimal("0")

    @property
    def earned_ton(self) -> Decimal:
        return self.balance_ton

    @property
    def earned_usdt(self) -> Decimal:
        return self.balance_usdt
