from decimal import Decimal

from app.core.enums import Currency


def format_amount(amount: Decimal) -> str:
    """Render a fixed-point amount without insignificant trailing zeroes."""
    rendered = format(amount, "f")
    if "." not in rendered:
        return rendered
    return rendered.rstrip("0").rstrip(".") or "0"


def currency_label(currency: Currency | str) -> str:
    normalized = Currency(currency)
    return "GRAM" if normalized is Currency.TON else normalized.value
