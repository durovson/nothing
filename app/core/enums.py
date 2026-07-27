from enum import StrEnum


class Language(StrEnum):
    RU = "ru"
    EN = "en"


class Currency(StrEnum):
    TON = "TON"
    USDT = "USDT"


class AdminDisputeAction(StrEnum):
    OPEN = "open"
    RELEASE = "release"
    REFUND = "refund"


class AdminAction(StrEnum):
    DISPUTES = "disputes"
    BROADCAST = "broadcast"
    MAINTENANCE = "maintenance"
    MAINTENANCE_ON = "maintenance_on"
    MAINTENANCE_OFF = "maintenance_off"
    BACK = "back"


class TonNetwork(StrEnum):
    MAINNET = "mainnet"
    TESTNET = "testnet"


class WalletVersion(StrEnum):
    V4R2 = "v4r2"
    V5R1 = "v5r1"


class DealType(StrEnum):
    OFFER = "offer"
    GIFTS = "gifts"
    CHANNEL = "channel"
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
