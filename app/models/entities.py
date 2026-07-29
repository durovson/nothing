from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import (
    CollectionStatus,
    Currency,
    DealStatus,
    DealType,
    DisputeStatus,
    FinancialAttemptStatus,
    FinancialOperationFlow,
    FinancialOperationStatus,
    FinancialOperationType,
    Language,
    PayoutStatus,
    ReferralWithdrawalStatus,
    RefundStatus,
    SystemMode,
    UnmatchedPaymentStatus,
    WalletVersion,
)


class User(BaseModel):
    telegram_id: int
    username: str | None = None
    wallet_address: str | None = None
    language: Language = Language.RU
    referrer_id: int | None = None
    created_at: datetime | None = None


class Deal(BaseModel):
    id: int
    public_id: str
    subwallet_id: int
    wallet_version: WalletVersion
    creator_id: int
    buyer_id: int | None = None
    seller_wallet_address: str | None = None
    buyer_wallet_address: str | None = None
    buyer_wallet_snapshot: str | None = None
    deal_type: DealType
    description: str
    currency: Currency
    amount: Decimal
    channel_id: int | None = None
    channel_title: str | None = None
    channel_username: str | None = None
    channel_access_granted_at: datetime | None = None
    channel_access_error: str | None = None
    channel_owner_verified_at: datetime | None = None
    channel_last_member_status: str | None = None
    channel_last_checked_at: datetime | None = None
    status: DealStatus
    wallet_address: str | None = None
    paid_tx_hash: str | None = None
    payout_tx_hash: str | None = None
    paid_tx_lt: int | None = None
    paid_amount_atomic: int | None = None
    payment_sender: str | None = None
    payment_memo_missing: bool = False
    paid_at: datetime | None = None
    custody_confirmed_at: datetime | None = None
    delivery_deadline_at: datetime | None = None
    delivered_at: datetime | None = None
    inspection_deadline_at: datetime | None = None
    resolution: str | None = None
    resolution_reason: str | None = None
    failure_reason: str | None = None
    cancellation_requested_at: datetime | None = None
    archived_at: datetime | None = None
    archived_reason: str | None = None
    success_feed_notified_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CollectionAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: CollectionStatus
    destination: str
    comment: str
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PayoutAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: PayoutStatus
    destination: str
    amount_atomic: int
    comment: str
    reward_destination: str | None = None
    reward_nominal_amount_atomic: int | None = None
    reward_comment: str | None = None
    currency: Currency = Currency.TON
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RefundAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: RefundStatus
    destination: str
    amount_atomic: int
    comment: str
    reason: str
    currency: Currency = Currency.TON
    reward_destination: str | None = None
    reward_nominal_amount_atomic: int | None = None
    reward_comment: str | None = None
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReferralWithdrawal(BaseModel):
    id: int
    user_id: int
    currency: Currency
    amount: Decimal
    amount_atomic: int
    destination: str
    comment: str
    status: ReferralWithdrawalStatus
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DisputeTicket(BaseModel):
    id: int
    deal_id: int
    opened_by: int
    status: DisputeStatus
    description: str
    resolution: str | None = None
    resolution_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BotSettings(BaseModel):
    id: int = 1
    maintenance_enabled: bool = False
    maintenance_message: str = "Технический перерыв. Попробуйте позже."
    updated_at: datetime | None = None


class SystemSetting(BaseModel):
    key: str
    value: str
    reason: str | None = None
    automatic: bool = False
    updated_by: int | None = None
    updated_at: datetime | None = None

    @property
    def mode(self) -> SystemMode:
        return SystemMode(self.value)


class FinancialOperation(BaseModel):
    id: int
    operation_id: str
    idempotency_key: str
    flow: FinancialOperationFlow
    type: FinancialOperationType
    status: FinancialOperationStatus
    currency: Currency
    amount_atomic: int
    destination: str
    comment: str
    deal_id: int | None = None
    referral_withdrawal_id: int | None = None
    unmatched_payment_id: int | None = None
    tx_hash: str | None = None
    retry_count: int = 0
    last_error: str | None = None
    next_retry_at: datetime | None = None
    locked_until: datetime | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FinancialOperationAttempt(BaseModel):
    id: int
    operation_id: int
    attempt_no: int
    status: FinancialAttemptStatus
    external_message_hash: str
    signed_boc: str
    valid_until: datetime
    tx_hash: str | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DepositCursor(BaseModel):
    scanner: str
    account_address: str
    last_lt: int | None = None
    last_hash: str | None = None
    updated_at: datetime | None = None


class ObservedDeposit(BaseModel):
    id: int
    tx_hash: str
    tx_lt: int
    currency: Currency
    amount_atomic: int
    sender: str | None = None
    memo: str | None = None
    account_address: str
    jetton_master_address: str | None = None
    jetton_wallet_address: str | None = None
    observed_at: datetime
    matched_deal_id: int | None = None
    processed_at: datetime | None = None
    created_at: datetime | None = None


class UnmatchedPayment(BaseModel):
    id: int
    observed_deposit_id: int
    tx_hash: str
    tx_lt: int
    currency: Currency
    amount_atomic: int
    sender: str | None = None
    memo: str | None = None
    reason: str
    status: UnmatchedPaymentStatus
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
