from enum import StrEnum
from typing import Any

from app.core.enums import Language


class TextKey(StrEnum):
    MAIN_MENU_CAPTION = "main_menu_caption"
    MENU_WALLET = "menu_wallet"
    MENU_CREATE_DEAL = "menu_create_deal"
    MENU_MY_DEALS = "menu_my_deals"
    MENU_SETTINGS = "menu_settings"
    WALLET_CAPTION = "wallet_caption"
    WALLET_EMPTY = "wallet_empty"
    WALLET_ADD = "wallet_add"
    WALLET_CHANGE = "wallet_change"
    WALLET_DELETE = "wallet_delete"
    WALLET_DELETED = "wallet_deleted"
    WALLET_PROMPT = "wallet_prompt"
    WALLET_SAVED = "wallet_saved"
    WALLET_INVALID = "wallet_invalid"
    DEAL_CREATE_INTRO = "deal_create_intro"
    DEAL_TYPE_GIFTS = "deal_type_gifts"
    DEAL_TYPE_CHANNEL = "deal_type_channel"
    DEAL_TYPE_ACCOUNT = "deal_type_account"
    DEAL_CHANNEL_WARNING = "deal_channel_warning"
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
    DEAL_REFRESH_BUTTON = "deal_refresh_button"
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
    SETTINGS_CAPTION = "settings_caption"
    SETTINGS_REFERRALS = "settings_referrals"
    SETTINGS_LANGUAGE = "settings_language"
    SETTINGS_SUPPORT = "settings_support"
    LANGUAGE_SAVED = "language_saved"
    SUPPORT_TEXT = "support_text"
    REFERRAL_CAPTION = "referral_caption"
    BACK_BUTTON = "back_button"
    LANG_RU = "lang_ru"
    LANG_EN = "lang_en"


TEXTS: dict[Language, dict[TextKey, str]] = {
    Language.RU: {
        TextKey.MAIN_MENU_CAPTION: (
            "Gift Guarant\n\nБезопасные escrow-сделки в Telegram.\n"
            "Комиссия сервиса: 1%\nПоддержка: {support_username}"
        ),
        TextKey.MENU_WALLET: "Мой кошелек",
        TextKey.MENU_CREATE_DEAL: "Создать сделку",
        TextKey.MENU_MY_DEALS: "Мои сделки",
        TextKey.MENU_SETTINGS: "Настройки",
        TextKey.WALLET_CAPTION: (
            "Ваш привязанный кошелек:\n{wallet}\n\n"
            "Этот адрес используется для вывода средств после завершения сделки."
        ),
        TextKey.WALLET_EMPTY: "Кошелек пока не привязан.",
        TextKey.WALLET_ADD: "Добавить кошелек",
        TextKey.WALLET_CHANGE: "Изменить кошелек",
        TextKey.WALLET_DELETE: "Удалить кошелек",
        TextKey.WALLET_DELETED: "Кошелек удален.",
        TextKey.WALLET_PROMPT: "Отправьте TON-адрес, который нужно привязать к профилю.",
        TextKey.WALLET_SAVED: "Кошелек сохранен: {wallet}",
        TextKey.WALLET_INVALID: "Похоже, это не TON-адрес. Проверьте формат и отправьте еще раз.",
        TextKey.DEAL_CREATE_INTRO: "Выберите тип сделки.",
        TextKey.DEAL_TYPE_GIFTS: "Подарки",
        TextKey.DEAL_TYPE_CHANNEL: "Канал",
        TextKey.DEAL_TYPE_ACCOUNT: "Аккаунт",
        TextKey.DEAL_CHANNEL_WARNING: "Сделка по каналу.\n\n{warning}\n\nОпишите, что именно передается.",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "Укажите описание сделки.\n\nНапример: аккаунт 2018 года, Cap или Telegram-канал с 10k подписчиков."
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "Выберите валюту сделки.",
        TextKey.DEAL_AMOUNT_PROMPT: "Введите сумму сделки числом. Например: 5 или 12.5",
        TextKey.DEAL_AMOUNT_INVALID: "Введите положительное число.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "Минимальная сумма сделки — {minimum} {currency}. "
            "Комиссия сервиса добавляется к счёту; сетевой gas оплачивается отдельно."
        ),
        TextKey.DEAL_CREATED: (
            "Сделка #{deal_id} создана.\n\nТип: {deal_type}\nОписание: {description}\n"
            "Продавец получит: {amount} {currency}\nПокупатель оплатит: {payment_amount} {currency}\n"
            "Escrow-адрес: {wallet_address}\nОбязательный комментарий: {deal_id}\n"
            "Ссылка покупателя: {deep_link}\n\n"
            "После оплаты у продавца 24 часа на передачу. После отметки передачи у покупателя "
            "3 часа для подарка или 24 часа для аккаунта/канала на подтверждение либо спор. "
            "Молчание продавца означает возврат, молчание покупателя — автоматическую выплату. "
            "Комиссия сервиса 1% удерживается при любом исходе; при возврате покупатель получает сумму сделки D."
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Отменить сделку",
        TextKey.DEAL_CONFIRM_BUTTON: "Подтвердить получение",
        TextKey.DEAL_DELIVER_BUTTON: "Товар передан",
        TextKey.DEAL_DISPUTE_BUTTON: "Открыть спор",
        TextKey.DEAL_REFRESH_BUTTON: "Обновить",
        TextKey.DEAL_JOINED: (
            "Сделка #{deal_id}\n\nТип: {deal_type}\nОписание: {description}\n"
            "Сумма: {amount} {currency}\nАдрес оплаты: {wallet_address}\n"
            "Обязательный комментарий: {deal_id}\n\nПосле оплаты бот автоматически проверит перевод. "
            "Привязанный TON-кошелёк используется для безопасного возврата. "
            "Комиссия сервиса 1% невозвратная; при refund возвращается сумма сделки D."
        ),
        TextKey.DEAL_NOT_FOUND: "Сделка не найдена.",
        TextKey.DEAL_FORBIDDEN: "У вас нет доступа к этой сделке.",
        TextKey.DEAL_ALREADY_CANCELLED: "Эту сделку уже нельзя отменить.",
        TextKey.DEAL_CANCELLED: "Сделка отменена.",
        TextKey.DEAL_LIST_EMPTY: "У вас пока нет сделок.",
        TextKey.DEAL_LIST_CAPTION: "Ваши сделки:",
        TextKey.DEAL_CARD: (
            "Сделка #{deal_id}\nСтатус: {status}\nТип: {deal_type}\nОписание: {description}\n"
            "Сумма: {amount} {currency}\nEscrow-адрес: {wallet_address}\n"
            "Комментарий: {deal_id}\nПокупатель: {buyer}\n"
            "Дедлайн передачи: {delivery_deadline}\nДедлайн проверки: {inspection_deadline}"
        ),
        TextKey.DEAL_PAID_BUYER: "Средства поступили на кошелёк гаранта. Ожидайте передачу товара.",
        TextKey.DEAL_PAID_SELLER: (
            "Покупатель оплатил сделку.\n"
            "Ссылка на транзакцию:\n{transaction_url}\n\n"
            "Передайте товар и нажмите «Товар передан» в карточке сделки."
        ),
        TextKey.DEAL_RELEASE_ACCEPTED: (
            "Получение подтверждено. Выплата продавцу поставлена в очередь; "
            "окончательное уведомление придёт после подтверждения сети TON."
        ),
        TextKey.DEAL_CONFIRMED: "Сделка завершена, выплата продавцу подтверждена сетью TON.",
        TextKey.DEAL_WAIT_WALLET: "У продавца не привязан кошелек для выплаты.",
        TextKey.DEAL_BUYER_WALLET_REQUIRED: (
            "Перед вступлением в сделку привяжите TON-кошелёк в разделе «Мой кошелёк». "
            "Он нужен как безопасный адрес возврата."
        ),
        TextKey.DEAL_PAYOUT_BLOCKED: (
            "Выплата остановлена до отправки: на кошельке гаранта недостаточно gas. "
            "Средства остаются у гаранта; обратитесь в поддержку."
        ),
        TextKey.DEAL_DELIVERED: "Передача отмечена. Покупатель получил срок на проверку.",
        TextKey.DEAL_DELIVERY_NOTICE: (
            "Продавец отметил товар переданным. Подтвердите получение или откройте спор до дедлайна. "
            "Если вы не ответите, выплата продавцу начнётся автоматически."
        ),
        TextKey.DEAL_DISPUTE_PROMPT: (
            "Опишите проблему одним сообщением (10–1000 символов). Скриншоты в боте не хранятся; "
            "при необходимости отправьте их напрямую @not_jammm."
        ),
        TextKey.DEAL_DISPUTE_INVALID: "Описание должно содержать от 10 до 1000 символов.",
        TextKey.DEAL_DISPUTE_CREATED: (
            "Спорный тикет создан. Средства заморожены у гаранта. "
            "Для разбора напишите @not_jammm и укажите ID сделки."
        ),
        TextKey.DEAL_REFUNDED: "Возврат покупателю подтверждён сетью TON.",
        TextKey.SETTINGS_CAPTION: "Настройки",
        TextKey.SETTINGS_REFERRALS: "Рефералы",
        TextKey.SETTINGS_LANGUAGE: "Язык",
        TextKey.SETTINGS_SUPPORT: "Поддержка",
        TextKey.LANGUAGE_SAVED: "Язык переключен: {language}.",
        TextKey.SUPPORT_TEXT: "По вопросам и спорам напишите {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "Ваша реферальная ссылка:\n{link}\n\nПриглашено: {count}\nЗаработано GRAM: {earned_ton}\nЗаработано USDT: {earned_usdt}"
        ),
        TextKey.BACK_BUTTON: "Назад",
        TextKey.LANG_RU: "Русский",
        TextKey.LANG_EN: "English",
    },
    Language.EN: {
        TextKey.MAIN_MENU_CAPTION: (
            "Gift Guarant\n\nSafe Telegram escrow deals.\n"
            "Service fee: 1%\nSupport: {support_username}"
        ),
        TextKey.MENU_WALLET: "My wallet",
        TextKey.MENU_CREATE_DEAL: "Create deal",
        TextKey.MENU_MY_DEALS: "My deals",
        TextKey.MENU_SETTINGS: "Settings",
        TextKey.WALLET_CAPTION: (
            "Your linked wallet:\n{wallet}\n\n"
            "This address is used for seller payouts after the deal is completed."
        ),
        TextKey.WALLET_EMPTY: "No wallet linked yet.",
        TextKey.WALLET_ADD: "Add wallet",
        TextKey.WALLET_CHANGE: "Change wallet",
        TextKey.WALLET_DELETE: "Delete wallet",
        TextKey.WALLET_DELETED: "Wallet deleted.",
        TextKey.WALLET_PROMPT: "Send the TON address you want to link to your profile.",
        TextKey.WALLET_SAVED: "Wallet saved: {wallet}",
        TextKey.WALLET_INVALID: "This does not look like a TON address. Please try again.",
        TextKey.DEAL_CREATE_INTRO: "Choose the deal type.",
        TextKey.DEAL_TYPE_GIFTS: "Gifts",
        TextKey.DEAL_TYPE_CHANNEL: "Channel",
        TextKey.DEAL_TYPE_ACCOUNT: "Account",
        TextKey.DEAL_CHANNEL_WARNING: "Channel deal.\n\n{warning}\n\nDescribe what exactly is being transferred.",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "Describe what is being transferred.\n\nExample: 2018 Telegram account or a 10k subscriber channel."
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "Choose the deal currency.",
        TextKey.DEAL_AMOUNT_PROMPT: "Enter the amount as a number. Example: 5 or 12.5",
        TextKey.DEAL_AMOUNT_INVALID: "Please enter a positive number.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "The minimum deal amount is {minimum} {currency}. "
            "The service fee is added to the invoice; network gas is paid separately."
        ),
        TextKey.DEAL_CREATED: (
            "Deal #{deal_id} created.\n\nType: {deal_type}\nDescription: {description}\n"
            "Seller receives: {amount} {currency}\nBuyer pays: {payment_amount} {currency}\n"
            "Escrow address: {wallet_address}\nRequired comment: {deal_id}\nBuyer link: {deep_link}\n\n"
            "The seller has 24 hours after payment to deliver. The buyer then has 3 hours for a gift "
            "or 24 hours for an account/channel to confirm or dispute. Seller silence means refund; "
            "buyer silence after delivery means automatic release. The 1% service fee is retained in every outcome; "
            "a refund returns the deal principal D."
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Cancel deal",
        TextKey.DEAL_CONFIRM_BUTTON: "Confirm receipt",
        TextKey.DEAL_DELIVER_BUTTON: "Item delivered",
        TextKey.DEAL_DISPUTE_BUTTON: "Open dispute",
        TextKey.DEAL_REFRESH_BUTTON: "Refresh",
        TextKey.DEAL_JOINED: (
            "Deal #{deal_id}\n\nType: {deal_type}\nDescription: {description}\nAmount: {amount} {currency}\n"
            "Payment address: {wallet_address}\nRequired comment: {deal_id}\n\n"
            "After payment, the bot verifies the transfer automatically. Link your TON wallet first; "
            "it is used as the safe refund destination. The 1% service fee is non-refundable; a refund returns D."
        ),
        TextKey.DEAL_NOT_FOUND: "Deal not found.",
        TextKey.DEAL_FORBIDDEN: "You do not have access to this deal.",
        TextKey.DEAL_ALREADY_CANCELLED: "This deal can no longer be cancelled.",
        TextKey.DEAL_CANCELLED: "Deal cancelled.",
        TextKey.DEAL_LIST_EMPTY: "You do not have any deals yet.",
        TextKey.DEAL_LIST_CAPTION: "Your deals:",
        TextKey.DEAL_CARD: (
            "Deal #{deal_id}\nStatus: {status}\nType: {deal_type}\nDescription: {description}\n"
            "Amount: {amount} {currency}\nEscrow address: {wallet_address}\n"
            "Comment: {deal_id}\nBuyer: {buyer}\n"
            "Delivery deadline: {delivery_deadline}\nInspection deadline: {inspection_deadline}"
        ),
        TextKey.DEAL_PAID_BUYER: "Funds reached the guarant wallet. Please wait for the item transfer.",
        TextKey.DEAL_PAID_SELLER: (
            "The buyer paid the deal.\n"
            "Transaction:\n{transaction_url}\n\n"
            "Transfer the item and press ‘Item delivered’ in the deal card."
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
            "the bot; send them directly to @not_jammm if needed."
        ),
        TextKey.DEAL_DISPUTE_INVALID: "Description must contain 10 to 1000 characters.",
        TextKey.DEAL_DISPUTE_CREATED: (
            "Dispute ticket created. Funds are frozen with the guarant. "
            "Contact @not_jammm and include the deal ID."
        ),
        TextKey.DEAL_REFUNDED: "The TON network confirmed the buyer refund.",
        TextKey.SETTINGS_CAPTION: "Settings",
        TextKey.SETTINGS_REFERRALS: "Referrals",
        TextKey.SETTINGS_LANGUAGE: "Language",
        TextKey.SETTINGS_SUPPORT: "Support",
        TextKey.LANGUAGE_SAVED: "Language switched: {language}.",
        TextKey.SUPPORT_TEXT: "For support or disputes, contact {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "Your referral link:\n{link}\n\nInvited: {count}\nEarned GRAM: {earned_ton}\nEarned USDT: {earned_usdt}"
        ),
        TextKey.BACK_BUTTON: "Back",
        TextKey.LANG_RU: "Русский",
        TextKey.LANG_EN: "English",
    },
}


def translate(locale: Language | str, key: TextKey, **kwargs: Any) -> str:
    try:
        language = Language(locale)
    except ValueError:
        language = Language.RU
    return TEXTS[language][key].format(**kwargs)
