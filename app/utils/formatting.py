from decimal import Decimal
from html import escape

from app.core.custom_emoji import CustomEmoji
from app.core.enums import ChannelMemberStatus, Currency, DealStatus, DealType, Language


_SUCCESSFUL_DEAL_STATUSES = frozenset({DealStatus.COMPLETED, DealStatus.REFUNDED})
_FAILED_DEAL_STATUSES = frozenset(
    {
        DealStatus.COLLECTION_FAILED,
        DealStatus.PAYOUT_FAILED,
        DealStatus.PAYOUT_BOUNCED,
        DealStatus.REFUND_FAILED,
        DealStatus.REFUND_BOUNCED,
        DealStatus.CANCELLED,
        DealStatus.CREATION_FAILED,
    }
)


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
        return "Ожидание оплаты" if locale is Language.RU else "Waiting for payment"
    if normalized in {
        DealStatus.COLLECTING,
        DealStatus.COLLECTION_SUBMITTED,
        DealStatus.PAID,
        DealStatus.DELIVERY_PENDING,
    }:
        return "Ожидание оказания услуги" if locale is Language.RU else "Waiting for delivery"
    if normalized is DealStatus.DELIVERED:
        return "Ожидание подтверждения покупателя" if locale is Language.RU else "Waiting for buyer confirmation"
    if normalized is DealStatus.DISPUTED:
        return "Открыт спор" if locale is Language.RU else "Dispute opened"
    if normalized in {
        DealStatus.RELEASE_REQUESTED,
        DealStatus.PAYOUT_PROCESSING,
        DealStatus.PAYOUT_SUBMITTED,
    }:
        return "Выплата обрабатывается" if locale is Language.RU else "Payout processing"
    if normalized in {
        DealStatus.REFUND_AWAITING_WALLET,
        DealStatus.REFUND_REQUESTED,
        DealStatus.REFUND_PROCESSING,
        DealStatus.REFUND_SUBMITTED,
    }:
        return "Возврат обрабатывается" if locale is Language.RU else "Refund processing"
    if normalized is DealStatus.COMPLETED:
        return "Завершена" if locale is Language.RU else "Completed"
    if normalized is DealStatus.REFUNDED:
        return "Возвращена" if locale is Language.RU else "Refunded"
    if normalized is DealStatus.CANCELLED:
        return "Отменена" if locale is Language.RU else "Cancelled"
    return "Ошибка" if locale is Language.RU else "Failed"


def deal_status_custom_emoji(status: DealStatus | str) -> CustomEmoji:
    """Map every deal status to one of the three approved status icons."""
    normalized = DealStatus(status)
    if normalized in _SUCCESSFUL_DEAL_STATUSES:
        return CustomEmoji.CONFIRM
    if normalized in _FAILED_DEAL_STATUSES:
        return CustomEmoji.CANCEL
    return CustomEmoji.PENDING


def deal_status_fallback_emoji(status: DealStatus | str) -> str:
    """Return a Unicode status marker suitable for inline button text."""
    return {
        CustomEmoji.CONFIRM: "✅",
        CustomEmoji.PENDING: "🕒",
        CustomEmoji.CANCEL: "❌",
    }[deal_status_custom_emoji(status)]


def deal_status_html(
    status: DealStatus | str,
    locale: Language = Language.RU,
    *,
    transaction_url: str | None = None,
) -> str:
    """Render a localized status with a Telegram custom emoji entity."""
    icon = deal_status_custom_emoji(status)
    fallback = deal_status_fallback_emoji(status)
    label = deal_status_label(status, locale)
    if transaction_url:
        label = f'<a href="{escape(transaction_url, quote=True)}">{label}</a>'
    return (
        f"{label} "
        f'<tg-emoji emoji-id="{icon.value}">{fallback}</tg-emoji>'
    )


def channel_member_status_label(
    status: ChannelMemberStatus | str | None,
    locale: Language = Language.RU,
) -> str:
    if status is None:
        return "ещё не проверен" if locale is Language.RU else "not checked yet"
    try:
        normalized = ChannelMemberStatus(status)
    except ValueError:
        normalized = ChannelMemberStatus.UNKNOWN
    labels = {
        ChannelMemberStatus.OWNER: ("владелец ✅", "owner ✅"),
        ChannelMemberStatus.ADMINISTRATOR: ("администратор", "administrator"),
        ChannelMemberStatus.MEMBER: ("участник", "member"),
        ChannelMemberStatus.ABSENT: ("не вступил", "not joined"),
        ChannelMemberStatus.UNKNOWN: ("проверка недоступна", "check unavailable"),
    }
    return labels[normalized][0 if locale is Language.RU else 1]
