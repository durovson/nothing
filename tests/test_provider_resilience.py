import unittest

from aiogram.types import CallbackQuery, Chat, Message, Update, User
from tonutils.exceptions import ProviderResponseError

from app.core.exceptions import TonProviderTemporaryError
from app.middleware.fast_callback import (
    callback_from_event,
    is_fast_navigation_callback,
)
from app.tasks.deal_monitor import provider_retry_delay
from app.ton.client import _raise_temporary_provider_error


class ProviderResilienceTests(unittest.TestCase):
    def test_retryable_provider_errors_are_translated(self) -> None:
        for code in (429, 500, 502, 503, 504, 542):
            with self.subTest(code=code):
                error = ProviderResponseError(
                    code=code,
                    message="temporary",
                    endpoint="/transactions",
                )
                with self.assertRaises(TonProviderTemporaryError) as raised:
                    _raise_temporary_provider_error(error)
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(raised.exception.endpoint, "/transactions")

    def test_authentication_provider_error_is_not_hidden(self) -> None:
        error = ProviderResponseError(
            code=401,
            message="unauthorized",
            endpoint="/transactions",
        )
        with self.assertRaises(ProviderResponseError) as raised:
            _raise_temporary_provider_error(error)
        self.assertIs(raised.exception, error)

    def test_provider_retry_delay_is_exponential_and_bounded(self) -> None:
        self.assertEqual(
            [provider_retry_delay(15, attempt) for attempt in range(1, 8)],
            [15, 30, 60, 120, 240, 300, 300],
        )

    def test_read_only_navigation_is_acknowledged_early(self) -> None:
        callbacks = (
            "menu:deals",
            "settings:language",
            "page:open:2",
            "deal:open:42",
            "deal-type:offer",
            "currency:TON",
            "language:ru",
        )
        for data in callbacks:
            with self.subTest(data=data):
                self.assertTrue(is_fast_navigation_callback(data))

    def test_actions_with_alerts_or_mutations_are_not_acknowledged_early(self) -> None:
        callbacks = (
            "menu:create",
            "wallet:open",
            "wallet:delete",
            "deal:cancel:42",
            "referral:withdraw:TON",
        )
        for data in callbacks:
            with self.subTest(data=data):
                self.assertFalse(is_fast_navigation_callback(data))

    def test_callback_is_extracted_from_dispatcher_update(self) -> None:
        telegram_user = User(id=1, is_bot=False, first_name="User")
        callback = CallbackQuery(
            id="query",
            from_user=telegram_user,
            chat_instance="chat",
            data="menu:deals",
            message=Message(
                message_id=1,
                date=0,
                chat=Chat(id=1, type="private"),
                from_user=telegram_user,
            ),
        )
        update = Update(update_id=1, callback_query=callback)

        self.assertIs(callback_from_event(update), callback)
