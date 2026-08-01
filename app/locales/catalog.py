import re
from enum import StrEnum
from html import escape
from pathlib import Path
from string import Formatter
from typing import Any

from app.core.enums import Language


class TextKey(StrEnum):
    MAIN_MENU_CAPTION = "main_menu_caption"
    MENU_WALLET = "menu_wallet"
    MENU_CREATE_DEAL = "menu_create_deal"
    MENU_MY_DEALS = "menu_my_deals"
    MENU_SETTINGS = "menu_settings"
    MENU_FAQ = "menu_faq"
    MENU_DOCUMENTS = "menu_documents"
    WALLET_CAPTION = "wallet_caption"
    WALLET_EMPTY = "wallet_empty"
    WALLET_ADD = "wallet_add"
    WALLET_CHANGE = "wallet_change"
    WALLET_DELETE = "wallet_delete"
    WALLET_DELETED = "wallet_deleted"
    WALLET_PROMPT = "wallet_prompt"
    WALLET_ACTIVE_PROMPT = "wallet_active_prompt"
    WALLET_SAVED = "wallet_saved"
    WALLET_INVALID = "wallet_invalid"
    WALLET_OPEN = "wallet_open"
    DEAL_CREATE_INTRO = "deal_create_intro"
    DEAL_TYPE_GIFTS = "deal_type_gifts"
    DEAL_TYPE_OFFER = "deal_type_offer"
    DEAL_TYPE_CHANNEL = "deal_type_channel"
    DEAL_TYPE_ACCOUNT = "deal_type_account"
    DEAL_CHANNEL_WARNING = "deal_channel_warning"
    DEAL_CHANNEL_INVALID = "deal_channel_invalid"
    DEAL_CHANNEL_VERIFIED = "deal_channel_verified"
    DEAL_CHANNEL_INVITE_UNAVAILABLE = "deal_channel_invite_unavailable"
    DEAL_PAY_BUTTON = "deal_pay_button"
    DEAL_CHANNEL_JOIN_BUTTON = "deal_channel_join_button"
    DEAL_DESCRIPTION_PROMPT = "deal_description_prompt"
    DEAL_CURRENCY_PROMPT = "deal_currency_prompt"
    DEAL_AMOUNT_PROMPT = "deal_amount_prompt"
    DEAL_AMOUNT_INVALID = "deal_amount_invalid"
    DEAL_AMOUNT_TOO_SMALL = "deal_amount_too_small"
    DEAL_CREATED = "deal_created"
    DEAL_CANCEL_BUTTON = "deal_cancel_button"
    DEAL_CONFIRM_BUTTON = "deal_confirm_button"
    DEAL_DELIVER_BUTTON = "deal_deliver_button"
    DEAL_DISPUTE_BUTTON = "deal_dispute_button"
    DEAL_JOINED = "deal_joined"
    DEAL_NOT_FOUND = "deal_not_found"
    DEAL_FORBIDDEN = "deal_forbidden"
    DEAL_ALREADY_CANCELLED = "deal_already_cancelled"
    DEAL_CANCELLED = "deal_cancelled"
    DEAL_LIST_EMPTY = "deal_list_empty"
    DEAL_LIST_CAPTION = "deal_list_caption"
    DEAL_CARD = "deal_card"
    DEAL_PAID_BUYER = "deal_paid_buyer"
    DEAL_PAID_SELLER = "deal_paid_seller"
    DEAL_CHANNEL_PAID_BUYER = "deal_channel_paid_buyer"
    DEAL_CHANNEL_PAID_SELLER = "deal_channel_paid_seller"
    DEAL_RELEASE_ACCEPTED = "deal_release_accepted"
    DEAL_CONFIRMED = "deal_confirmed"
    DEAL_WAIT_WALLET = "deal_wait_wallet"
    DEAL_BUYER_WALLET_REQUIRED = "deal_buyer_wallet_required"
    DEAL_PAYOUT_BLOCKED = "deal_payout_blocked"
    DEAL_DELIVERED = "deal_delivered"
    DEAL_DELIVERY_NOTICE = "deal_delivery_notice"
    DEAL_DISPUTE_PROMPT = "deal_dispute_prompt"
    DEAL_DISPUTE_INVALID = "deal_dispute_invalid"
    DEAL_DISPUTE_CREATED = "deal_dispute_created"
    DEAL_REFUNDED = "deal_refunded"
    DEAL_CANCELLED_BY_SELLER = "deal_cancelled_by_seller"
    DEAL_PAYOUT_RECEIVED = "deal_payout_received"
    SETTINGS_CAPTION = "settings_caption"
    SETTINGS_REFERRALS = "settings_referrals"
    SETTINGS_LANGUAGE = "settings_language"
    SETTINGS_SUPPORT = "settings_support"
    LANGUAGE_PROMPT = "language_prompt"
    LANGUAGE_SAVED = "language_saved"
    SUPPORT_TEXT = "support_text"
    REFERRAL_CAPTION = "referral_caption"
    BACK_BUTTON = "back_button"
    MAIN_MENU_BUTTON = "main_menu_button"
    FAQ_CAPTION = "faq_caption"
    DOCUMENTS_CAPTION = "documents_caption"
    PRIVACY_BUTTON = "privacy_button"
    TERMS_BUTTON = "terms_button"
    SERVICE_DESCRIPTION_BUTTON = "service_description_button"
    LANG_RU = "lang_ru"
    LANG_EN = "lang_en"
    COMPLETED_DEAL_FEED = "completed_deal_feed"


TEXTS: dict[Language, dict[TextKey, str]] = {
    Language.RU: {
        TextKey.MAIN_MENU_CAPTION: (
            "<b>Для тех, кто ценит скорость и безопасность.</b>\n"
            "Проводите сделки без риска и сторонних посредников.\n\n"
            "<b>Главное о сервисе:</b>\n\n"
            "<blockquote>"
            "<tg-emoji emoji-id=\'5258093637450866522\'>🤖</tg-emoji> <b>Технология:</b>\n"
            "Прямая интеграция TON × Telegram\n\n"
            "<tg-emoji emoji-id=\'5879895758202735862\'>🔒</tg-emoji> <b>Безопасность:</b>\n"
            "Заморозка активов до завершения условий сделки\n\n"
            "<tg-emoji emoji-id=\'5778139491810155937\'>📊</tg-emoji> <b>Прозрачность:</b>\n"
            "Фиксированная комиссия — всего 1%"
            "</blockquote>\n\n"
            "<tg-emoji emoji-id=\'5994636050033545139\'>🪧</tg-emoji> <b>Успешные сделки:</b> "
            "<a href='https://t.me/grnthub/4'>@grnthub</a>"
        ),
        TextKey.MENU_WALLET: "Мой кошелек",
        TextKey.MENU_CREATE_DEAL: "Создать сделку",
        TextKey.MENU_MY_DEALS: "Мои сделки",
        TextKey.MENU_SETTINGS: "Настройки",
        TextKey.MENU_FAQ: "Вопросы",
        TextKey.MENU_DOCUMENTS: "Документы",
        TextKey.WALLET_CAPTION: (
            "💵 <b>Кошелёк</b>\n\n<a href=\"{wallet_url}\">{wallet_short}</a>\n\n"
            "<b>Полный адрес:</b> <code>{wallet}</code>"
        ),
        TextKey.WALLET_EMPTY: "💵 <b>Мой кошелёк</b>\n\nВыберите или добавьте ваш кошелёк по кнопке ниже:",
        TextKey.WALLET_ADD: "Добавить кошелек",
        TextKey.WALLET_CHANGE: "Изменить кошелек",
        TextKey.WALLET_DELETE: "Удалить кошелек",
        TextKey.WALLET_DELETED: "Кошелек удален.",
        TextKey.WALLET_PROMPT: "💰 <b>Мой кошелёк</b>\n\nОтправьте TON-адрес, который нужно привязать к профилю.",
        TextKey.WALLET_ACTIVE_PROMPT: (
            "💰 <b>Мой кошелёк</b>\n\nТекущий адрес:\n<code>{wallet}</code>\n\n"
            "Хотите изменить? Отправьте новый адрес."
        ),
        TextKey.WALLET_SAVED: "Кошелек сохранен: {wallet}",
        TextKey.WALLET_INVALID: "Похоже, это не TON-адрес. Проверьте формат и отправьте еще раз.",
        TextKey.WALLET_OPEN: "Открыть кошелёк",
        TextKey.DEAL_CREATE_INTRO: "💼 <b>Создание сделки</b>\n\nВыберите тип сделки 👇",
        TextKey.DEAL_TYPE_GIFTS: "Оффер",
        TextKey.DEAL_TYPE_OFFER: "🤝 Оффер",
        TextKey.DEAL_TYPE_CHANNEL: "Канал",
        TextKey.DEAL_TYPE_ACCOUNT: "Оффер",
        TextKey.DEAL_CHANNEL_WARNING: (
            "⭐️ <b>Сделка по каналу</b>\n\nДобавьте бота администратором канала и выдайте ему полные права, включая "
            "приглашение пользователей и назначение администраторов. Затем отправьте @username, ID канала "
            "или перешлите сообщение из канала.\n\nПокупатель вступит по инвайт-ссылке. После оплаты продавец вручную "
            "передаёт ему статус владельца. Бот автоматически проверяет статус и только после этого запускает выплату.\n\n"
            "<b>⚠️ Не удаляйте бота из администраторов до завершения сделки!</b>"
        ),
        TextKey.DEAL_CHANNEL_INVALID: (
            "⚠️ <b>Канал не прошёл проверку</b>\n\n{reason}\n\n"
            "<b>Исправьте права и отправьте канал ещё раз.</b>"
        ),
        TextKey.DEAL_CHANNEL_VERIFIED: "Канал «{title}» проверен.",
        TextKey.DEAL_CHANNEL_INVITE_UNAVAILABLE: (
            "Не удалось создать безопасную ссылку для входа в канал. Оплата пока недоступна. "
            "Продавцу нужно проверить, что бот всё ещё является администратором с правом приглашать пользователей."
        ),
        TextKey.DEAL_PAY_BUTTON: "Оплатить в Tonkeeper",
        TextKey.DEAL_CHANNEL_JOIN_BUTTON: "📢 Запросить доступ к каналу",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "💼 <b>Создание оффера</b>\n\nУкажите, что вы предлагаете в сделке.\n\n"
            "<blockquote>Например: цифровой товар, подарок, аккаунт или услуга и условия её оказания.</blockquote>"
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "💼 <b>Создание сделки</b>\n\nВыберите валюту сделки 👇",
        TextKey.DEAL_AMOUNT_PROMPT: "💼 <b>Создание сделки</b>\n\nВведите сумму сделки.\nНапример: <code>5</code> или <code>12.5</code>",
        TextKey.DEAL_AMOUNT_INVALID: "Введите положительное число.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "Минимальная сумма сделки — {minimum} {currency}. "
            "Комиссия сервиса добавляется к счёту; сетевой gas оплачивается отдельно."
        ),
        TextKey.DEAL_CREATED: (
            "✅ <b>Сделка #{deal_id} создана</b>\n\n<b>Детали сделки:</b>\n"
            "• Описание: {description}\n• Продавец получит: {amount} {currency}\n"
            "• Покупатель оплатит: {payment_amount} {currency}\n\n"
            "<blockquote>При возврате покупателю возвращается сумма сделки D; комиссия сервиса 1% удерживается.</blockquote>\n\n"
            "Для присоединения покупателя отправьте ему ссылку:\n{deep_link}"
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Отменить сделку",
        TextKey.DEAL_CONFIRM_BUTTON: "Завершить сделку",
        TextKey.DEAL_DELIVER_BUTTON: "Услуга оказана",
        TextKey.DEAL_DISPUTE_BUTTON: "Открыть спор",
        TextKey.DEAL_JOINED: (
            "💼 <b>Сделка #{deal_id}</b>\n\n👤 Вы покупатель.\n\n"
            "• Завершённых сделок продавца: {seller_deals}\n\n<b>Детали сделки:</b>\n"
            "• Код сделки: #{deal_id}\n• Описание: {description}\n\n"
            "<b>Адрес оплаты:</b>\n<code>{wallet_address}</code>\n\n"
            "<b>Сумма к оплате:</b>\n{amount} {currency}\n\n"
            "<b>Обязательный комментарий:</b>\n<code>{deal_id}</code>\n\n"
            "<blockquote>‼️ Пожалуйста, убедитесь, что при оплате указываете обязательный комментарий (memo) и точную сумму!</blockquote>\n"
            "<blockquote>При возврате возвращается сумма сделки D; комиссия сервиса 1% удерживается.</blockquote>\n"
            "После оплаты бот автоматически проверит перевод."
        ),
        TextKey.DEAL_NOT_FOUND: "Сделка не найдена.",
        TextKey.DEAL_FORBIDDEN: "У вас нет доступа к этой сделке.",
        TextKey.DEAL_ALREADY_CANCELLED: "Эту сделку уже нельзя отменить.",
        TextKey.DEAL_CANCELLED: "Сделка отменена.",
        TextKey.DEAL_LIST_EMPTY: "Здесь пока ничего нет",
        TextKey.DEAL_LIST_CAPTION: "<b>Мои сделки:</b>",
        TextKey.DEAL_CARD: (
            "📋 <b>Сделка #{deal_id}</b>\n\n<b>Детали сделки:</b>\n"
            "• Описание: {description}\n• Продавец получит: {amount} {currency}\n"
            "• Покупатель оплатит: {payment_amount} {currency}\n\n"
            "<b>Продавец:</b> {seller}\n<b>Покупатель:</b> {buyer}{channel_details}\n\n"
            "<b>Статус:</b> {status}"
        ),
        TextKey.DEAL_PAID_BUYER: (
            "✅ <b>Оплата найдена и подтверждена!</b>\n\nВаш платеж по сделке #{deal_id} успешно обработан.\n\n"
            "<b>Детали сделки:</b>\n• Описание: {description}\n• Продавец: {seller}\n\n"
            "Транзакция:\n<a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "⏳ Ожидайте подтверждения оказания услуги от продавца."
        ),
        TextKey.DEAL_PAID_SELLER: (
            "💰 <b>Оплата подтверждена!</b>\n\nПокупатель оплатил сделку #{deal_id}\n\n"
            "<b>Детали сделки:</b>\n• Описание: {description}\n• Покупатель: {buyer}\n\n"
            "<a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "✅ Средства зачислены на кошелёк бота.\n📦 Теперь вы можете приступить к оказанию услуги. Не забудьте нажать кнопку ниже!"
        ),
        TextKey.DEAL_CHANNEL_PAID_BUYER: (
            "✅ Оплата сделки #{deal_id} подтверждена и удерживается гарантом.\nТранзакция:\n{transaction_url}\n\n"
            "Вступите в канал по кнопке сделки и дождитесь, "
            "пока продавец вручную передаст вам статус владельца. Бот проверит это автоматически."
        ),
        TextKey.DEAL_CHANNEL_PAID_SELLER: (
            "✅ Покупатель оплатил сделку #{deal_id}. Вручную передайте ему статус владельца в настройках Telegram и не удаляйте "
            "бота из администраторов. После статуса creator бот автоматически запустит выплату.\n\nТранзакция:\n{transaction_url}"
        ),
        TextKey.DEAL_RELEASE_ACCEPTED: (
            "✅ <b>Сделка завершена!</b>\n\n<b>Детали сделки:</b>\nОписание: {description}\n"
            "Продавец получил: {seller_amount} {currency}\nПокупатель оплатил: {payment_amount} {currency}\n\n"
            "Выплата продавцу обрабатывается. Он получит уведомление после завершения транзакции.\n\n"
            "Спасибо за использование нашего сервиса! 🙏"
        ),
        TextKey.DEAL_CONFIRMED: "✅ Сделка успешно завершена",
        TextKey.DEAL_WAIT_WALLET: "У продавца не привязан кошелек для выплаты.",
        TextKey.DEAL_BUYER_WALLET_REQUIRED: (
            "Перед вступлением в сделку привяжите TON-кошелёк в разделе «Мой кошелёк». "
            "Он нужен как безопасный адрес возврата."
        ),
        TextKey.DEAL_PAYOUT_BLOCKED: (
            "Выплата остановлена до отправки: на кошельке гаранта недостаточно gas. "
            "Средства остаются у гаранта; обратитесь в поддержку."
        ),
        TextKey.DEAL_DELIVERED: "✅ <b>Услуга отмечена как оказанная!</b>\n\nПокупатель получил уведомление и может подтвердить получение.",
        TextKey.DEAL_DELIVERY_NOTICE: (
            "✅ <b>Продавец оказал услугу!</b>\n\nПродавец подтвердил, что оказал услугу по сделке:\n"
            "• Код сделки: #{deal_id}\n• Описание: {description}\n• Сумма к оплате: {payment_amount} {currency}\n\n"
            "Пожалуйста, проверьте качество выполненной работы.\n\n"
            "⚠️ После вашего подтверждения средства будут переведены продавцу.\n\n"
            "Если в течение 1 часа вы не подтвердите получение товара и не откроете спор, "
            "сделка будет завершена автоматически."
        ),
        TextKey.DEAL_DISPUTE_PROMPT: (
            "Опишите проблему одним сообщением (10–1000 символов). Скриншоты в боте не хранятся; "
            "при необходимости отправьте их напрямую в службу поддержки."
        ),
        TextKey.DEAL_DISPUTE_INVALID: "Описание должно содержать от 10 до 1000 символов.",
        TextKey.DEAL_DISPUTE_CREATED: (
            "Спорный тикет создан. Средства заморожены у гаранта. "
            "Для разбора напишите в службу поддержки и укажите ID сделки."
        ),
        TextKey.DEAL_REFUNDED: "Возврат покупателю подтверждён сетью TON.",
        TextKey.DEAL_CANCELLED_BY_SELLER: "Сделка отменена продавцом\nКод сделки: #{deal_id}",
        TextKey.DEAL_PAYOUT_RECEIVED: (
            "💰 <b>Выплата получена!</b>\n\n<b>Детали сделки:</b>\n• Описание: {description}\n"
            "• Сумма: {amount} {currency}\n• Статус: ✅ Сделка успешно завершена\n"
            "• Кошелек: <code>{wallet}</code>\n\n"
            "🔗 <a href=\"{transaction_url}\">Посмотреть транзакцию</a>\n\n"
            "Спасибо за использование нашего сервиса! 🙏"
        ),
        TextKey.SETTINGS_CAPTION: "⚙️ <b>Настройки</b>",
        TextKey.SETTINGS_REFERRALS: "Рефералы",
        TextKey.SETTINGS_LANGUAGE: "Язык",
        TextKey.SETTINGS_SUPPORT: "Поддержка",
        TextKey.LANGUAGE_PROMPT: (
            "🇷🇺 → Выберите язык бота прежде чем начать пользоваться.\n\n"
            "🇺🇸 → Choose the bot's language before you start using it."
        ),
        TextKey.LANGUAGE_SAVED: (
            "🎉 <b>Язык успешно установлен!</b>\n\n"
            "<blockquote>Нажмите на кнопку ниже чтобы перейти в главное меню. 👇</blockquote>"
        ),
        TextKey.SUPPORT_TEXT: "🛟 <b>Поддержка</b>\n\nПо вопросам и спорам напишите {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "⭐️ <b>Реф. система</b>\n\nРеферальный процент: {rate} %\n"
            "Приглашено пользователей: {count}\n\nGRAM: {earned_ton}\nUSDT(TON): {earned_usdt}\n\n"
            "<b>Ваша реферальная ссылка:</b>\n<code>{link}</code>"
        ),
        TextKey.BACK_BUTTON: "Назад",
        TextKey.MAIN_MENU_BUTTON: "Главное меню",
        TextKey.FAQ_CAPTION: (
            "📚 <b>Помощь и часто задаваемые вопросы</b>\n\n<b>Как использовать сервис:</b>\n\n"
            "1. Добавьте свой TON-кошелёк в разделе «Мой кошелёк».\n2. Создайте сделку или присоединитесь к существующей.\n"
            "3. Покупатель переводит средства — они замораживаются на escrow.\n4. После оказания услуги покупатель подтверждает — деньги автоматически уходят продавцу.\n\n"
            "<b>Как долго заморожены деньги?</b>\nДо подтверждения покупателем или отмены сделки.\n\n"
            "<b>Что если продавец не выполнил работу?</b>\nВы можете отменить сделку и вернуть средства до подтверждения.\n\n"
            "<b>Сколько стоит комиссия?</b>\nФиксировано 1% от суммы сделки.\n\n"
            "<b>Можно ли торговать криптовалютой, товарами или услугами?</b>\nДа, любые сделки между двумя пользователями.\n\n"
            "<b>Что делать, если возник спор?</b>\nНапишите в поддержку {support_username}.\n\n"
            "<b>Как работает реферальная система?</b>\nВы получаете 10% от комиссии сервиса по завершённым сделкам приглашённых пользователей.\n\n"
            "<b>Нужна помощь?</b> Свяжитесь с поддержкой: {support_username}"
        ),
        TextKey.DOCUMENTS_CAPTION: "📄 <b>Документы</b>\n\nВыберите документ:",
        TextKey.PRIVACY_BUTTON: "Политика конфиденциальности",
        TextKey.TERMS_BUTTON: "Пользовательское соглашение",
        TextKey.SERVICE_DESCRIPTION_BUTTON: "Описание и условия сервиса",
        TextKey.LANG_RU: "Русский",
        TextKey.LANG_EN: "English",
        TextKey.COMPLETED_DEAL_FEED: (
            "<b>Сделка:</b> <code>#{deal_id}</code>\n\n"
            "<b>Детали сделки:</b>\n"
            "<b>• Описание:</b> <code>{description}</code>\n"
            "<b>• Сумма:</b> <code>{amount} {currency}</code>\n\n"
            "@grntrobot"
        ),
    },
    Language.EN: {
        TextKey.MAIN_MENU_CAPTION: (
            "<b>For those who value speed and security.</b> Make deals without unnecessary intermediaries.\n\n"
            "🤖 <b>Technology:</b> Direct TON × Telegram integration\n\n"
            "✋ <b>Security:</b> Assets are frozen until conditions are completed\n\n"
            "📊 <b>Transparency:</b> Fixed 1% fee\n\n💬 <b>Reviews:</b> <a href=\"https://t.me/grnthub/4\">@grnthub</a>"
        ),
        TextKey.MENU_WALLET: "My wallet",
        TextKey.MENU_CREATE_DEAL: "Create deal",
        TextKey.MENU_MY_DEALS: "My deals",
        TextKey.MENU_SETTINGS: "Settings",
        TextKey.MENU_FAQ: "Questions",
        TextKey.MENU_DOCUMENTS: "Documents",
        TextKey.WALLET_CAPTION: (
            "💵 <b>Wallet</b>\n\n<a href=\"{wallet_url}\">{wallet_short}</a>\n\n"
            "<b>Full address:</b> <code>{wallet}</code>"
        ),
        TextKey.WALLET_EMPTY: "💵 <b>My wallet</b>\n\nSelect or add your wallet below:",
        TextKey.WALLET_ADD: "Add wallet",
        TextKey.WALLET_CHANGE: "Change wallet",
        TextKey.WALLET_DELETE: "Delete wallet",
        TextKey.WALLET_DELETED: "Wallet deleted.",
        TextKey.WALLET_PROMPT: "💰 <b>My wallet</b>\n\nSend the TON address you want to link to your profile.",
        TextKey.WALLET_ACTIVE_PROMPT: (
            "💰 <b>My wallet</b>\n\nCurrent address:\n<code>{wallet}</code>\n\n"
            "Want to change it? Send a new address."
        ),
        TextKey.WALLET_SAVED: "Wallet saved: {wallet}",
        TextKey.WALLET_INVALID: "This does not look like a TON address. Please try again.",
        TextKey.WALLET_OPEN: "Open wallet",
        TextKey.DEAL_CREATE_INTRO: "💼 <b>Create a deal</b>\n\nChoose the deal type 👇",
        TextKey.DEAL_TYPE_GIFTS: "Offer",
        TextKey.DEAL_TYPE_OFFER: "🤝 Offer",
        TextKey.DEAL_TYPE_CHANNEL: "Channel",
        TextKey.DEAL_TYPE_ACCOUNT: "Offer",
        TextKey.DEAL_CHANNEL_WARNING: (
            "📢 <b>Channel deal</b>\n\nAdd the bot as a channel administrator with <b>full rights</b>, including inviting users "
            "and promoting administrators. Then send the @username, numeric channel ID, or forward a channel message.\n\n"
            "The buyer joins through the invite link. After payment, the seller manually transfers ownership. "
            "The bot verifies the <code>creator</code> status and only then queues payout. "
            "<blockquote>Keep the bot as an administrator until the deal is complete.</blockquote>"
        ),
        TextKey.DEAL_CHANNEL_INVALID: "Channel validation failed: {reason}\n\nFix the permissions and send the channel again.",
        TextKey.DEAL_CHANNEL_VERIFIED: "Channel “{title}” verified.",
        TextKey.DEAL_CHANNEL_INVITE_UNAVAILABLE: (
            "A secure channel invite link could not be created, so payment is unavailable. "
            "The seller must verify that the bot is still an administrator with permission to invite users."
        ),
        TextKey.DEAL_PAY_BUTTON: "Pay in Tonkeeper",
        TextKey.DEAL_CHANNEL_JOIN_BUTTON: "📢 Request channel access",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "💼 <b>Create an offer</b>\n\nDescribe what you offer in the deal.\n\n"
            "<blockquote>Example: a digital item, gift, account, service, and its delivery terms.</blockquote>"
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "💼 <b>Create a deal</b>\n\nChoose the deal currency 👇",
        TextKey.DEAL_AMOUNT_PROMPT: "💼 <b>Create a deal</b>\n\nEnter the deal amount.\nExample: <code>5</code> or <code>12.5</code>",
        TextKey.DEAL_AMOUNT_INVALID: "Please enter a positive number.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "The minimum deal amount is {minimum} {currency}. "
            "The service fee is added to the invoice; network gas is paid separately."
        ),
        TextKey.DEAL_CREATED: (
            "✅ <b>Deal #{deal_id} created</b>\n\n<b>Type:</b> {deal_type}\n<b>Description:</b> {description}\n"
            "<b>Seller receives:</b> {amount} {currency}\n<b>Buyer pays:</b> {payment_amount} {currency}\n\n"
            "💰 <b>Escrow address:</b>\n<code>{wallet_address}</code>\n"
            "📝 <b>Required comment:</b> <code>{deal_id}</code>\n"
            "🔗 <a href=\"{deep_link}\">Buyer link</a>\n\n"
            "For an offer, the seller has 1 hour after payment to deliver and the buyer has 1 hour to confirm or dispute. "
            "For a channel, the seller manually transfers ownership and the bot verifies it automatically. Seller silence means refund; "
            "buyer silence after delivery means automatic release. The 1% service fee is retained in every outcome; "
            "a refund returns the deal principal D."
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Cancel deal",
        TextKey.DEAL_CONFIRM_BUTTON: "Complete deal",
        TextKey.DEAL_DELIVER_BUTTON: "Service delivered",
        TextKey.DEAL_DISPUTE_BUTTON: "Open dispute",
        TextKey.DEAL_JOINED: (
            "💼 <b>Deal #{deal_id}</b>\n\n👤 You are the buyer.\n\n"
            "• Seller completed deals: {seller_deals}\n\n<b>Deal details:</b>\n"
            "• Deal code: #{deal_id}\n• Description: {description}\n\n"
            "<b>Payment address:</b>\n<code>{wallet_address}</code>\n\n"
            "<b>Amount due:</b>\n{amount} {currency}\n\n"
            "<b>Required comment:</b>\n<code>{deal_id}</code>\n\n"
            "<blockquote>‼️ Use the exact amount and required comment (memo).</blockquote>\n"
            "The bot verifies payment automatically. A refund returns D; the 1% service fee is retained."
        ),
        TextKey.DEAL_NOT_FOUND: "Deal not found.",
        TextKey.DEAL_FORBIDDEN: "You do not have access to this deal.",
        TextKey.DEAL_ALREADY_CANCELLED: "This deal can no longer be cancelled.",
        TextKey.DEAL_CANCELLED: "Deal cancelled.",
        TextKey.DEAL_LIST_EMPTY: "Nothing here yet",
        TextKey.DEAL_LIST_CAPTION: "<b>My deals:</b>",
        TextKey.DEAL_CARD: (
            "📋 <b>Deal #{deal_id}</b>\n\n<b>Deal details:</b>\n"
            "• Description: {description}\n• Seller receives: {amount} {currency}\n"
            "• Buyer pays: {payment_amount} {currency}\n\n"
            "<b>Seller:</b> {seller}\n<b>Buyer:</b> {buyer}{channel_details}\n\n"
            "<b>Status:</b> {status}"
        ),
        TextKey.DEAL_PAID_BUYER: "Funds reached the guarant wallet. Please wait for the item transfer.",
        TextKey.DEAL_PAID_SELLER: (
            "The buyer paid deal #{deal_id}.\nDescription: {description}\nBuyer: {buyer}\n"
            "Transaction:\n{transaction_url}\n\n"
            "Transfer the item and press ‘Item delivered’ in the deal card."
        ),
        TextKey.DEAL_CHANNEL_PAID_BUYER: (
            "✅ Channel deal #{deal_id} payment is confirmed and held by the guarant.\nTransaction:\n{transaction_url}\n\n"
            "Join through the deal button and wait for the seller "
            "to transfer ownership. The bot verifies it automatically."
        ),
        TextKey.DEAL_CHANNEL_PAID_SELLER: (
            "✅ The buyer paid channel deal #{deal_id}. Transfer ownership manually in Telegram and keep the bot as administrator. "
            "Payout is queued automatically only after creator status is verified.\n\nTransaction:\n{transaction_url}"
        ),
        TextKey.DEAL_RELEASE_ACCEPTED: (
            "Receipt confirmed. The seller payout was queued; "
            "a final notification will arrive after TON network confirmation."
        ),
        TextKey.DEAL_CONFIRMED: "The deal is complete and the TON network confirmed the seller payout.",
        TextKey.DEAL_WAIT_WALLET: "The seller has no payout wallet linked yet.",
        TextKey.DEAL_BUYER_WALLET_REQUIRED: (
            "Link a TON wallet before joining. It is required as the safe refund destination."
        ),
        TextKey.DEAL_PAYOUT_BLOCKED: (
            "Payout was stopped before broadcast because the guarant wallet lacks gas. "
            "Funds remain with the guarant; contact support."
        ),
        TextKey.DEAL_DELIVERED: "Delivery marked. The buyer inspection period has started.",
        TextKey.DEAL_DELIVERY_NOTICE: (
            "The seller marked the item delivered. Confirm receipt or open a dispute before the deadline. "
            "Silence starts automatic seller payout."
        ),
        TextKey.DEAL_DISPUTE_PROMPT: (
            "Describe the problem in one message (10–1000 characters). Screenshots are not stored by "
            "the bot; send them directly to support if needed."
        ),
        TextKey.DEAL_DISPUTE_INVALID: "Description must contain 10 to 1000 characters.",
        TextKey.DEAL_DISPUTE_CREATED: (
            "Dispute ticket created. Funds are frozen with the guarant. "
            "Contact support and include the deal ID."
        ),
        TextKey.DEAL_REFUNDED: "The TON network confirmed the buyer refund.",
        TextKey.DEAL_CANCELLED_BY_SELLER: "The seller cancelled deal #{deal_id}.",
        TextKey.DEAL_PAYOUT_RECEIVED: (
            "💰 <b>Payout received!</b>\n\n<b>Deal details:</b>\n• Description: {description}\n"
            "• Amount: {amount} {currency}\n• Status: ✅ Successfully completed\n"
            "• Wallet: <code>{wallet}</code>\n\n"
            "🔗 <a href=\"{transaction_url}\">View transaction</a>\n\nThank you for using our service! 🙏"
        ),
        TextKey.SETTINGS_CAPTION: "⚙️ <b>Settings</b>",
        TextKey.SETTINGS_REFERRALS: "Referrals",
        TextKey.SETTINGS_LANGUAGE: "Language",
        TextKey.SETTINGS_SUPPORT: "Support",
        TextKey.LANGUAGE_PROMPT: (
            "🇷🇺 → Выберите язык бота прежде чем начать пользоваться.\n\n"
            "🇺🇸 → Choose the bot's language before you start using it."
        ),
        TextKey.LANGUAGE_SAVED: (
            "🎉 <b>Language successfully set!</b>\n\n"
            "<blockquote>Press the button below to open the main menu. 👇</blockquote>"
        ),
        TextKey.SUPPORT_TEXT: "🛟 <b>Support</b>\n\nFor support or disputes, contact {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "👥 <b>Referral program</b>\n\n<b>Reward:</b> {rate}% of the service fee from completed referred deals\n"
            "<b>Invited:</b> {count}\n<b>GRAM balance:</b> {earned_ton}\n<b>USDT balance:</b> {earned_usdt}\n\n"
            "🔗 <b>Your link:</b>\n<code>{link}</code>\n\n"
            "Withdrawals go to the linked address. Exchanges, custodial services and third-party "
            "wallets may require extra metadata and are used at your own risk."
        ),
        TextKey.BACK_BUTTON: "Back",
        TextKey.MAIN_MENU_BUTTON: "Main menu",
        TextKey.FAQ_CAPTION: (
            "📚 <b>Help and frequently asked questions</b>\n\n"
            "Add a TON wallet, create or join a deal, fund escrow, and confirm delivery to release funds.\n\n"
            "<b>How long are funds frozen?</b> Until buyer confirmation or cancellation.\n\n"
            "<b>Service fee:</b> fixed 1%.\n\n<b>Disputes:</b> contact {support_username}.\n\n"
            "Referral reward is 10% of the service fee generated by completed deals of invited users."
        ),
        TextKey.DOCUMENTS_CAPTION: "📄 <b>Documents</b>\n\nChoose a document:",
        TextKey.PRIVACY_BUTTON: "Privacy policy",
        TextKey.TERMS_BUTTON: "Terms of service",
        TextKey.SERVICE_DESCRIPTION_BUTTON: "Service description and conditions",
        TextKey.LANG_RU: "Русский",
        TextKey.LANG_EN: "English",
        TextKey.COMPLETED_DEAL_FEED: (
            "<b>Deal:</b> <code>#{deal_id}</code>\n\n"
            "<b>Deal details:</b>\n"
            "<b>• Description:</b> <code>{description}</code>\n"
            "<b>• Amount:</b> <code>{amount} {currency}</code>\n\n"
            "@grntrobot"
        ),
    },
}


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


def translate(locale: Language | str, key: TextKey, **kwargs: Any) -> str:
    try:
        language = Language(locale)
    except ValueError:
        language = Language.RU
    safe_kwargs = {name: escape(str(value), quote=True) for name, value in kwargs.items()}
    return TEXTS[language][key].format(**safe_kwargs)
