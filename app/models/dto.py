from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import Currency, DealType, DeskKind, Language, ReferralLevel


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


class CreateDeskListingCommand(BaseModel):
    public_id: str = Field(min_length=10, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    owner_id: int
    owner_username: str = Field(min_length=1, max_length=64)
    owner_language: Language
    kind: DeskKind
    description: str = Field(min_length=1, max_length=2_000)
    deal_currency: Currency
    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    payment_currency: Currency
    publication_fee: Decimal = Field(gt=Decimal("0"))
    publication_fee_atomic: int = Field(gt=0)
    payment_deadline_at: datetime


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
    level: ReferralLevel = ReferralLevel.LEVEL_1
    ton_volume: Decimal = Decimal("0")
    commission_share: Decimal = Decimal("0.10")

    @property
    def earned_ton(self) -> Decimal:
        return self.balance_ton

    @property
    def earned_usdt(self) -> Decimal:
        return self.balance_usdt


class ReferralProfile(BaseModel):
    user_id: int
    level: ReferralLevel = ReferralLevel.LEVEL_1
    ton_volume: Decimal = Decimal("0")

    @property
    def commission_share(self) -> Decimal:
        return {
            ReferralLevel.LEVEL_1: Decimal("0.10"),
            ReferralLevel.LEVEL_2: Decimal("0.20"),
            ReferralLevel.LEVEL_3: Decimal("0.30"),
            ReferralLevel.SPECIAL: Decimal("0.50"),
        }[self.level]
