import unittest
from html.parser import HTMLParser
from pathlib import Path

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.keyboards import deal_type_keyboard, main_menu
from app.locales.catalog import TEXTS, TextKey

TEXT_FILE = Path(__file__).parents[1] / "BOT_TEXTS_EDITABLE.txt"


class EditableTextsTests(unittest.TestCase):
    def test_file_contains_every_localized_block(self) -> None:
        content = TEXT_FILE.read_text(encoding="utf-8")
        expected = {f"[[{language.value}.{key.value}]]" for language in Language for key in TextKey}
        content_lines = content.splitlines()
        present = {line for line in content_lines if line.startswith("[[") and line != "[[/]]"}
        self.assertEqual(present, expected)
        self.assertEqual(content_lines.count("[[/]]"), len(expected))

    def test_requested_channel_copy_is_active(self) -> None:
        warning = TEXTS[Language.RU][TextKey.DEAL_CHANNEL_WARNING]
        invalid = TEXTS[Language.RU][TextKey.DEAL_CHANNEL_INVALID]
        self.assertIn('<tg-emoji emoji-id="5843843420468024653">⭐️</tg-emoji>', warning)
        self.assertIn("<b>Не удаляйте бота из администраторов", warning)
        self.assertIn("<b>Канал не прошёл проверку</b>", invalid)
        self.assertIn("{reason}", invalid)

    def test_telegram_html_blocks_are_balanced(self) -> None:
        class Parser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.stack: list[str] = []

            def handle_starttag(self, tag: str, attrs) -> None:
                del attrs
                self.stack.append(tag)

            def handle_endtag(self, tag: str) -> None:
                self.assert_next(tag)

            def assert_next(self, tag: str) -> None:
                if not self.stack or self.stack.pop() != tag:
                    raise AssertionError(f"Unbalanced Telegram HTML tag: {tag}")

        for language in Language:
            for key in TextKey:
                parser = Parser()
                parser.feed(TEXTS[language][key])
                parser.close()
                self.assertEqual(parser.stack, [], f"Unclosed tag in {language.value}.{key.value}")

    def test_premium_icons_are_native_in_main_buttons(self) -> None:
        buttons = [button for row in main_menu(Language.RU).inline_keyboard for button in row]
        self.assertEqual(buttons[0].icon_custom_emoji_id, CustomEmoji.WALLET.value)
        self.assertTrue(all(button.icon_custom_emoji_id for button in buttons))

        deal_types = deal_type_keyboard(Language.RU).inline_keyboard[0]
        self.assertEqual(deal_types[0].icon_custom_emoji_id, CustomEmoji.OFFER.value)
        self.assertEqual(deal_types[1].icon_custom_emoji_id, CustomEmoji.CHANNEL.value)

    def test_payment_templates_keep_required_placeholders(self) -> None:
        seller = TEXTS[Language.RU][TextKey.DEAL_PAID_SELLER]
        channel_buyer = TEXTS[Language.RU][TextKey.DEAL_CHANNEL_PAID_BUYER]
        self.assertIn("{description}", seller)
        self.assertIn("{buyer}", seller)
        self.assertIn("{transaction_url}", channel_buyer)


if __name__ == "__main__":
    unittest.main()
