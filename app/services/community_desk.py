from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from decimal import Decimal, InvalidOperation
from html import escape

from aiogram.types import MessageEntity
from aiogram.utils.text_decorations import add_surrogates, html_decoration

from app.api.telegram_notifier import TelegramNotificationGateway
from app.core.enums import Currency, DeskKind, Language
from app.models.dto import ParsedCommunityListing, ReferralCommunity
from app.models.entities import DeskListing
from app.repositories.desk import DeskRepository

_HEADER_RE = re.compile(
    r"(?im)^[\t ]*(?:┏┅[\t ]*/[\t ]*)?(WTS|WTB)(?:[\t ]*/)?[\t ]*$"
)
_ITEM_RE = re.compile(r"(?im)^[\t ]*(?:┣[\t ]*)?Item[\t ]*:[\t ]*")
_PRICE_RE = re.compile(
    r"(?im)^[\t ]*(?:┣[\t ]*)?Price[\t ]*:[\t ]*(?P<value>[^\r\n]+)"
)
_AMOUNT_RE = re.compile(
    r"^(?P<amount>\d+(?:[.,]\d{1,9})?)[\t ]*(?P<currency>GRAM|TON|USDT)$",
    re.IGNORECASE,
)
_INLINE_ENTITY_TYPES = frozenset(
    {
        "bold",
        "italic",
        "underline",
        "strikethrough",
        "spoiler",
        "code",
        "url",
        "text_link",
        "text_mention",
        "mention",
        "email",
        "phone_number",
        "custom_emoji",
    }
)


def looks_like_community_listing(text: str | None) -> bool:
    """Cheap handler pre-filter which avoids database calls for normal chat."""
    if not text:
        return False
    return bool(_HEADER_RE.search(text) and _ITEM_RE.search(text) and _PRICE_RE.search(text))


def parse_community_listing(
    text: str,
    entities: list[MessageEntity] | None = None,
) -> ParsedCommunityListing | None:
    """Parse the community format while preserving inline Telegram entities."""
    header = _HEADER_RE.search(text)
    if header is None:
        return None
    item = _ITEM_RE.search(text, header.end())
    if item is None:
        return None
    price_matches = list(_PRICE_RE.finditer(text, item.end()))
    if not price_matches:
        return None
    price = price_matches[-1]

    item_start = item.end()
    item_segment = text[item_start:price.start()].rstrip()
    lines = item_segment.splitlines(keepends=True)
    if lines and lines[-1].strip() in {"┋", "┃", "|"}:
        item_segment = "".join(lines[:-1]).rstrip()
    if not item_segment or len(item_segment) > 2_000:
        return None
    item_end = item_start + len(item_segment)

    price_value = price.group("value").strip().strip("/").strip()
    if price_value.casefold() == "offer":
        amount = None
        currency = Currency.TON
    else:
        amount_match = _AMOUNT_RE.fullmatch(price_value)
        if amount_match is None:
            return None
        try:
            amount = Decimal(amount_match.group("amount").replace(",", "."))
        except InvalidOperation:
            return None
        if amount <= 0 or -amount.as_tuple().exponent > 9:
            return None
        currency_name = amount_match.group("currency").upper()
        currency = Currency.USDT if currency_name == "USDT" else Currency.TON

    description_html = _unparse_inline_slice(
        text,
        item_start,
        item_end,
        entities or [],
    )
    if len(description_html) > 3_200:
        return None
    normalized = " ".join(
        unicodedata.normalize("NFKC", item_segment).casefold().split()
    )
    fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return ParsedCommunityListing(
        kind=DeskKind(header.group(1).upper()),
        description=item_segment,
        description_html=description_html,
        deal_currency=currency,
        price=amount,
        item_fingerprint=fingerprint,
    )


def _unparse_inline_slice(
    text: str,
    start: int,
    end: int,
    entities: list[MessageEntity],
) -> str:
    start_units = len(add_surrogates(text[:start])) // 2
    end_units = len(add_surrogates(text[:end])) // 2
    adjusted: list[MessageEntity] = []
    for entity in entities:
        entity_type = getattr(entity.type, "value", str(entity.type))
        entity_end = entity.offset + entity.length
        if (
            entity_type in _INLINE_ENTITY_TYPES
            and entity.offset >= start_units
            and entity_end <= end_units
        ):
            adjusted.append(
                entity.model_copy(update={"offset": entity.offset - start_units})
            )
    if not adjusted:
        return escape(text[start:end])
    return html_decoration.unparse(text[start:end], adjusted)


class CommunityDeskService:
    """Connect moderated communities and mirror their visible Desk posts."""

    def __init__(
        self,
        repository: DeskRepository,
        notifications: TelegramNotificationGateway,
    ) -> None:
        self._repository = repository
        self._notifications = notifications

    async def connect(
        self,
        *,
        chat_id: int,
        topic_id: int,
        name: str,
        username: str | None,
        owner_user_id: int,
    ) -> ReferralCommunity:
        return await self._repository.connect_community(
            chat_id=chat_id,
            topic_id=topic_id,
            name=name,
            username=username,
            owner_user_id=owner_user_id,
        )

    async def ingest(
        self,
        *,
        chat_id: int,
        topic_id: int,
        message_id: int,
        text: str,
        entities: list[MessageEntity] | None,
        owner_language: Language,
    ) -> DeskListing | None:
        parsed = parse_community_listing(text, entities)
        if parsed is None:
            return None
        listing = await self._repository.create_community_listing(
            public_id=secrets.token_hex(5),
            chat_id=chat_id,
            topic_id=topic_id,
            source_message_id=message_id,
            owner_language=owner_language,
            parsed=parsed,
        )
        if listing is None:
            # Disabled/unregistered communities and global duplicate Items are
            # intentionally indistinguishable to the public handler.
            return None
        published_message_id = await self._notifications.publish_community_desk_listing(
            listing
        )
        if published_message_id is None:
            await self._repository.mark_publication_failed(
                listing.id, "Telegram Community Desk publication failed"
            )
            return None
        return await self._repository.mark_published(
            listing.id, published_message_id
        )
