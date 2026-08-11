import re
from html import escape
from pathlib import Path
from string import Formatter
from typing import Any

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.locales.keys import TextKey
from app.locales.texts import TEXTS


_EDITABLE_TEXTS_PATH = Path(__file__).resolve().parents[2] / "BOT_TEXTS_EDITABLE.txt"
_BLOCK_START = re.compile(r"^\[\[(ru|en)\.([a-z0-9_]+)\]\]$")
_BLOCK_END = "[[/]]"


def _load_editable_texts(path: Path = _EDITABLE_TEXTS_PATH) -> None:
    """Overlay the built-in fallback catalog with UTF-8 editorial content."""
    if not path.is_file():
        return

    overrides: dict[tuple[Language, TextKey], str] = {}
    current: tuple[Language, TextKey] | None = None
    lines: list[str] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = _BLOCK_START.fullmatch(line)
        if match:
            if current is not None:
                raise RuntimeError(f"Nested text block at line {line_number}")
            try:
                current = (Language(match.group(1)), TextKey(match.group(2)))
            except ValueError as exc:
                raise RuntimeError(f"Unknown text key at line {line_number}: {line}") from exc
            if current in overrides:
                raise RuntimeError(f"Duplicate text block at line {line_number}: {line}")
            lines = []
            continue
        if line == _BLOCK_END:
            if current is None:
                raise RuntimeError(f"Unexpected text block end at line {line_number}")
            overrides[current] = "\n".join(lines)
            current = None
            lines = []
            continue
        if current is not None:
            lines.append(line)

    if current is not None:
        raise RuntimeError(f"Unclosed text block: {current[0].value}.{current[1].value}")

    expected = {(language, key) for language in Language for key in TextKey}
    missing = expected.difference(overrides)
    if missing:
        names = ", ".join(
            f"{language.value}.{key.value}"
            for language, key in sorted(
                missing, key=lambda item: (item[0].value, item[1].value)
            )
        )
        raise RuntimeError(f"BOT_TEXTS_EDITABLE.txt is missing blocks: {names}")

    for (language, key), value in overrides.items():
        try:
            supplied_fields = {
                field_name
                for _, field_name, _, _ in Formatter().parse(value)
                if field_name is not None
            }
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid braces in text block {language.value}.{key.value}"
            ) from exc
        allowed_fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(TEXTS[language][key])
            if field_name is not None
        }
        unknown_fields = supplied_fields.difference(allowed_fields)
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise RuntimeError(
                f"Unknown placeholders in {language.value}.{key.value}: {names}"
            )
        TEXTS[language][key] = value


_load_editable_texts()


_CUSTOM_EMOJI_TAG = re.compile(r"(<tg-emoji\b[^>]*>.*?</tg-emoji>)", re.DOTALL)
_CUSTOM_EMOJI_REPLACEMENTS: tuple[tuple[str, CustomEmoji], ...] = (
    ("🇷🇺", CustomEmoji.RUSSIAN),
    ("🇺🇸", CustomEmoji.ENGLISH),
    ("⚙️", CustomEmoji.SETTINGS),
    ("⚠️", CustomEmoji.WARNING),
    ("❗️", CustomEmoji.ALERT),
    ("‼️", CustomEmoji.ALERT),
    ("⭐️", CustomEmoji.CHANNEL),
    ("ℹ️", CustomEmoji.WARNING),
    ("◀️", CustomEmoji.BACK),
    ("🤖", CustomEmoji.ROBOT),
    ("🔒", CustomEmoji.LOCK),
    ("📊", CustomEmoji.STATS),
    ("🪧", CustomEmoji.REVIEWS),
    ("💵", CustomEmoji.WALLET),
    ("💰", CustomEmoji.MONEY),
    ("👛", CustomEmoji.WALLET),
    ("💼", CustomEmoji.CREATE_DEAL),
    ("👇", CustomEmoji.PERSON),
    ("🔖", CustomEmoji.OFFER),
    ("📢", CustomEmoji.SUPPORT),
    ("📋", CustomEmoji.DOCUMENTS),
    ("👤", CustomEmoji.REFERRALS),
    ("👥", CustomEmoji.REFERRALS),
    ("💎", CustomEmoji.TON),
    ("✅", CustomEmoji.CONFIRM),
    ("🔄", CustomEmoji.COMPLETE),
    ("🎉", CustomEmoji.CONFIRM),
    ("🛟", CustomEmoji.SUPPORT),
    ("📚", CustomEmoji.LANGUAGE),
    ("📄", CustomEmoji.DOCUMENTS),
    ("💬", CustomEmoji.OFFER),
    ("📝", CustomEmoji.DOCUMENTS),
    ("🔗", CustomEmoji.MESSAGE),
    ("🙏", CustomEmoji.PERSON),
    ("🐱", CustomEmoji.PERSON),
    ("📦", CustomEmoji.CHANNEL),
    ("⏳", CustomEmoji.WARNING),
    ("✋", CustomEmoji.PERSON),
    ("⚙", CustomEmoji.SETTINGS),
    ("⚠", CustomEmoji.WARNING),
    ("❗", CustomEmoji.ALERT),
    ("‼", CustomEmoji.ALERT),
    ("⭐", CustomEmoji.CHANNEL),
    ("ℹ", CustomEmoji.WARNING),
)


def _customize_emojis(text: str) -> str:
    """Replace Unicode emoji outside existing tags with Telegram custom emoji."""

    parts = _CUSTOM_EMOJI_TAG.split(text)
    for index in range(0, len(parts), 2):
        plain_text = parts[index]
        for symbol, emoji in _CUSTOM_EMOJI_REPLACEMENTS:
            plain_text = plain_text.replace(
                symbol,
                f'<tg-emoji emoji-id="{emoji.value}">{symbol}</tg-emoji>',
            )
        parts[index] = plain_text
    return "".join(parts)


for _language_texts in TEXTS.values():
    for _key, _value in _language_texts.items():
        _language_texts[_key] = _customize_emojis(_value)


def translate(locale: Language | str, key: TextKey, **kwargs: Any) -> str:
    try:
        language = Language(locale)
    except ValueError:
        language = Language.RU
    safe_kwargs = {name: escape(str(value), quote=True) for name, value in kwargs.items()}
    return TEXTS[language][key].format(**safe_kwargs)

