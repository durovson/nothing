from enum import StrEnum


class Language(StrEnum):
    RU = "ru"
    EN = "en"


class Currency(StrEnum):
    TON = "TON"
    USDT = "USDT"


class ReferralLevel(StrEnum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    SPECIAL = "special"


class DeskKind(StrEnum):
    WTS = "WTS"
    WTB = "WTB"


class DeskListingStatus(StrEnum):
    WAITING_PAYMENT = "waiting_payment"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    EXPIRED = "expired"
    PUBLICATION_FAILED = "publication_failed"


class AdminDisputeAction(StrEnum):
    OPEN = "open"
    RELEASE = "release"
    REFUND = "refund"


class AdminAction(StrEnum):
    DISPUTES = "disputes"
    FINANCIAL_OPERATIONS = "financial_operations"
    UNMATCHED_PAYMENTS = "unmatched_payments"
    BROADCAST = "broadcast"
    MAINTENANCE = "maintenance"
    MAINTENANCE_ON = "maintenance_on"
    MAINTENANCE_OFF = "maintenance_off"
    MODE_NORMAL = "mode_normal"
    MODE_READ_ONLY = "mode_read_only"
    MODE_EMERGENCY = "mode_emergency"
    BACK = "back"


class SystemMode(StrEnum):
    NORMAL = "normal"
    READ_ONLY = "read_only"
    EMERGENCY = "emergency"


class FinancialAdminAction(StrEnum):
    OPEN = "open"
    RETRY = "retry"
    REOPEN = "reopen"
    MANUAL_REVIEW = "manual_review"
    FORCE_COMPLETE = "force_complete"


class UnmatchedPaymentAction(StrEnum):
    OPEN = "open"
    REFUND = "refund"
    CONFIRM_REFUND = "confirm_refund"


class TonNetwork(StrEnum):
    MAINNET = "mainnet"
    TESTNET = "testnet"


class WalletVersion(StrEnum):
    V4R2 = "v4r2"
    V5R1 = "v5r1"


class DealType(StrEnum):
    OFFER = "offer"
    CHANNEL = "channel"
    # Persisted legacy values remain readable until historical deals are migrated.
    GIFTS = "gifts"
    ACCOUNT = "account"


class ChannelMemberStatus(StrEnum):
    OWNER = "creator"
    ADMINISTRATOR = "administrator"
    MEMBER = "member"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class DealStatus(StrEnum):
    CREATING = "creating"
    PENDING = "pending"
    COLLECTING = "collecting"
    COLLECTION_SUBMITTED = "collection_submitted"
    COLLECTION_FAILED = "collection_failed"
    PAID = "paid"
    DELIVERY_PENDING = "delivery_pending"
    DELIVERED = "delivered"
    DISPUTED = "disputed"
    RELEASE_REQUESTED = "release_requested"
    PAYOUT_PROCESSING = "payout_processing"
    PAYOUT_SUBMITTED = "payout_submitted"
    PAYOUT_FAILED = "payout_failed"
    PAYOUT_BOUNCED = "payout_bounced"
    REFUND_AWAITING_WALLET = "refund_awaiting_wallet"
    REFUND_REQUESTED = "refund_requested"
    REFUND_PROCESSING = "refund_processing"
    REFUND_SUBMITTED = "refund_submitted"
    REFUND_FAILED = "refund_failed"
    REFUND_BOUNCED = "refund_bounced"
    REFUNDED = "refunded"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CREATION_FAILED = "creation_failed"


class PayoutStatus(StrEnum):
    CREATING = "creating"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"


class CollectionStatus(StrEnum):
    CREATING = "creating"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"


class RefundStatus(StrEnum):
    CREATING = "creating"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"


class ReferralWithdrawalStatus(StrEnum):
    CREATING = "creating"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"


class FinancialOperationType(StrEnum):
    COLLECTION_TRANSFER = "collection_transfer"
    SELLER_TRANSFER = "seller_transfer"
    BUYER_REFUND = "buyer_refund"
    SERVICE_FEE_TRANSFER = "service_fee_transfer"
    REFERRAL_TRANSFER = "referral_transfer"


class FinancialOperationFlow(StrEnum):
    COLLECTION = "collection"
    PAYOUT = "payout"
    REFUND = "refund"
    REFERRAL = "referral"
    UNMATCHED_REFUND = "unmatched_refund"


class FinancialOperationStatus(StrEnum):
    PENDING = "pending"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    BOUNCED = "bounced"
    MANUAL_REVIEW = "manual_review"


class FinancialAttemptStatus(StrEnum):
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    BOUNCED = "bounced"
    UNKNOWN = "unknown"


class UnmatchedPaymentStatus(StrEnum):
    OPEN = "open"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    LINKED = "linked"
    IGNORED = "ignored"


class DisputeStatus(StrEnum):
    OPEN = "open"
    RESOLVED_RELEASE = "resolved_release"
    RESOLVED_REFUND = "resolved_refund"
    CLOSED = "closed"


class TraceStatus(StrEnum):
    NOT_FOUND = "not_found"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"
