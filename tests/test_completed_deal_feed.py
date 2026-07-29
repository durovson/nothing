import unittest
from decimal import Decimal

from app.api.telegram_notifier import TelegramNotificationGateway
from app.services.payouts import PayoutService
from tests.helpers import deal, settings


class RecordingBot:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, int | None]] = []

    async def send_message(
        self,
        chat_id: str,
        text: str,
        message_thread_id: int | None = None,
    ) -> None:
        self.messages.append((chat_id, text, message_thread_id))


class CompletedDealFeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_publishes_escaped_monospace_summary(self) -> None:
        bot = RecordingBot()
        gateway = TelegramNotificationGateway(bot, settings())  # type: ignore[arg-type]

        result = await gateway.completed_deal_feed(
            deal(
                status="completed",
                description="Оффер <test>",
                amount=Decimal("1.020000000"),
            )
        )

        self.assertTrue(result)
        self.assertEqual(bot.messages[0][0], "@grnthub")
        self.assertEqual(bot.messages[0][2], 4)
        self.assertEqual(
            bot.messages[0][1],
            "<b>Сделка:</b> <code>#abc123def0</code>\n\n"
            "<b>Детали сделки:</b>\n"
            "<b>•</b> <b>Описание:</b> <code>Оффер &lt;test&gt;</code>\n"
            "<b>•</b> <b>Сумма:</b> <code>1.02 GRAM</code>\n\n"
            "@grntrobot",
        )

    async def test_completed_deal_is_claimed_only_once(self) -> None:
        completed = deal(status="completed")

        class Deals:
            claimed = False

            async def list_completed_without_success_feed(self, limit: int = 20):
                del limit
                return [completed]

            async def claim_success_feed_notification(self, deal_id: int):
                del deal_id
                if self.claimed:
                    return None
                self.claimed = True
                return completed

            async def release_success_feed_notification(self, deal_id: int) -> None:
                del deal_id
                self.claimed = False

        class Notifications:
            published = 0

            async def completed_deal_feed(self, item) -> bool:
                del item
                self.published += 1
                return True

        deals = Deals()
        notifications = Notifications()
        service = PayoutService(
            settings(),
            deals,  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            notifications,  # type: ignore[arg-type]
        )

        await service.publish_pending_success_feed()
        await service.publish_pending_success_feed()

        self.assertEqual(notifications.published, 1)


if __name__ == "__main__":
    unittest.main()
