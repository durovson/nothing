from enum import StrEnum

from aiogram.filters.callback_data import CallbackData

from app.core.enums import Currency, DealType, Language


class MenuAction(StrEnum):
    BACK = "back"


class WalletAction(StrEnum):
    EDIT = "edit"
    DELETE = "delete"


class DealAction(StrEnum):
    OPEN = "open"
    CANCEL = "cancel"
    CONFIRM = "confirm"


class PageAction(StrEnum):
    OPEN = "open"
    CURRENT = "current"


class SettingsAction(StrEnum):
    BACK = "back"
    REFERRALS = "referrals"
    LANGUAGE = "language"
    SUPPORT = "support"


class MenuCallback(CallbackData, prefix="menu"):
    action: MenuAction


class WalletCallback(CallbackData, prefix="wallet"):
    action: WalletAction


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


class LanguageCallback(CallbackData, prefix="language"):
    language: Language

