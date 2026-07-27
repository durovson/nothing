from decimal import Decimal

from app.core.enums import Currency, DealStatus, DealType, Language


def format_amount(amount: Decimal) -> str:
    """Render a fixed-point amount without insignificant trailing zeroes."""
    rendered = format(amount, "f")
    if "." not in rendered:
        return rendered
    return rendered.rstrip("0").rstrip(".") or "0"


def currency_label(currency: Currency | str) -> str:
    normalized = Currency(currency)
    return "GRAM" if normalized is Currency.TON else normalized.value


def deal_type_label(deal_type: DealType | str, locale: Language = Language.RU) -> str:
    normalized = DealType(deal_type)
    if normalized is DealType.CHANNEL:
        return "Канал" if locale is Language.RU else "Channel"
    return "Оффер" if locale is Language.RU else "Offer"


def deal_status_label(
    status: DealStatus | str,
    locale: Language = Language.RU,
) -> str:
    normalized = DealStatus(status)
    if normalized in {DealStatus.CREATING, DealStatus.PENDING}:
        return "Ожидание ⏳" if locale is Language.RU else "Waiting ⏳"
    if normalized in {
        DealStatus.COLLECTING,
        DealStatus.COLLECTION_SUBMITTED,
        DealStatus.PAID,
        DealStatus.DELIVERY_PENDING,
        DealStatus.DELIVERED,
    }:
        return "Активная 🟢" if locale is Language.RU else "Active 🟢"
    if normalized is DealStatus.DISPUTED:
        return "Спор ⚖️" if locale is Language.RU else "Dispute ⚖️"
    if normalized in {
        DealStatus.RELEASE_REQUESTED,
        DealStatus.PAYOUT_PROCESSING,
        DealStatus.PAYOUT_SUBMITTED,
    }:
        return "Выплата 💸" if locale is Language.RU else "Payout 💸"
    if normalized in {
        DealStatus.REFUND_AWAITING_WALLET,
        DealStatus.REFUND_REQUESTED,
        DealStatus.REFUND_PROCESSING,
        DealStatus.REFUND_SUBMITTED,
    }:
        return "Возврат ↩️" if locale is Language.RU else "Refund ↩️"
    if normalized is DealStatus.COMPLETED:
        return "Завершена ✅" if locale is Language.RU else "Completed ✅"
    if normalized is DealStatus.REFUNDED:
        return "Возвращена ↩️" if locale is Language.RU else "Refunded ↩️"
    if normalized is DealStatus.CANCELLED:
        return "Отменена 🔴" if locale is Language.RU else "Cancelled 🔴"
    return "Ошибка ❌" if locale is Language.RU else "Failed ❌"
