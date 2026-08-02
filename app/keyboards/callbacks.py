from enum import StrEnum

from aiogram.filters.callback_data import CallbackData

from app.core.enums import (
    AdminAction,
    AdminDisputeAction,
    Currency,
    DealType,
    FinancialAdminAction,
    Language,
    UnmatchedPaymentAction,
)


class MenuAction(StrEnum):
    BACK = "back"
    WALLET = "wallet"
    CREATE_DEAL = "create"
    DEALS = "deals"
    SETTINGS = "settings"
    REFERRALS = "referrals"
    FAQ = "faq"
    DOCUMENTS = "documents"


class DealAction(StrEnum):
    OPEN = "open"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    DELIVER = "deliver"
    DISPUTE = "dispute"


class PageAction(StrEnum):
    OPEN = "open"
    CURRENT = "current"


class SettingsAction(StrEnum):
    BACK = "back"
    REFERRALS = "referrals"
    LANGUAGE = "language"
    SUPPORT = "support"


class ReferralAction(StrEnum):
    WITHDRAW = "withdraw"


class MenuCallback(CallbackData, prefix="menu"):
    action: MenuAction


class DealTypeCallback(CallbackData, prefix="deal-type"):
    deal_type: DealType


class CurrencyCallback(CallbackData, prefix="currency"):
    currency: Currency


class DealCallback(CallbackData, prefix="deal"):
    action: DealAction
    deal_id: int


class PageCallback(CallbackData, prefix="page"):
    action: PageAction
    page: int


class SettingsCallback(CallbackData, prefix="settings"):
    action: SettingsAction


class ReferralCallback(CallbackData, prefix="referral"):
    action: ReferralAction
    currency: Currency


class LanguageCallback(CallbackData, prefix="language"):
    language: Language


class AdminCallback(CallbackData, prefix="admin"):
    action: AdminAction


class AdminDisputeCallback(CallbackData, prefix="adm-dsp"):
    action: AdminDisputeAction
    ticket_id: int
    page: int = 0


class AdminFinancialCallback(CallbackData, prefix="adm-fin"):
    action: FinancialAdminAction
    operation_id: int
    page: int = 0


class AdminUnmatchedCallback(CallbackData, prefix="adm-unm"):
    action: UnmatchedPaymentAction
    payment_id: int
    page: int = 0
