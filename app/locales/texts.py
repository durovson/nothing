from app.core.enums import Language
from app.locales.keys import TextKey


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
            "<tg-emoji emoji-id='5769403330761593044'>💵</tg-emoji> <b>Кошелёк</b>\n\n<a href=\"{wallet_url}\">{wallet_short}</a>\n\n"
            "<b>Полный адрес:</b>\n<blockquote><code>{wallet}</code></blockquote>"
        ),
        TextKey.WALLET_EMPTY: "<tg-emoji emoji-id='5769403330761593044'>💵</tg-emoji> <b>Мой кошелёк</b>\n\nВыберите или добавьте ваш кошелёк по кнопке ниже:",
        TextKey.WALLET_ADD: "Добавить кошелек",
        TextKey.WALLET_CHANGE: "Изменить кошелек",
        TextKey.WALLET_DELETE: "Удалить кошелек",
        TextKey.WALLET_DELETED: "Кошелек удален.",
        TextKey.WALLET_PROMPT: "<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>Мой кошелёк</b>\n\nОтправьте TON-адрес, который нужно привязать к профилю.",
        TextKey.WALLET_ACTIVE_PROMPT: (
            "<tg-emoji emoji-id='5769403330761593044'>👛</tg-emoji> <b>Мой кошелёк</b>\n\nТекущий адрес:\n"
            "<blockquote><code>{wallet}</code></blockquote>\n\n"
            "Хотите изменить? Отправьте новый адрес."
        ),
        TextKey.WALLET_SAVED: "Кошелек сохранен:\n<blockquote><code>{wallet}</code></blockquote>",
        TextKey.WALLET_INVALID: "Похоже, это не TON-адрес. Проверьте формат и отправьте еще раз.",
        TextKey.WALLET_OPEN: "Открыть кошелёк",
        TextKey.DEAL_CREATE_INTRO: "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Создание сделки</b>\n\nВыберите тип сделки <tg-emoji emoji-id='5908808657700655253'>👇</tg-emoji>",
        TextKey.DEAL_TYPE_GIFTS: "Оффер",
        TextKey.DEAL_TYPE_OFFER: "Оффер",
        TextKey.DEAL_TYPE_CHANNEL: "Канал",
        TextKey.DEAL_TYPE_ACCOUNT: "Оффер",
        TextKey.DEAL_CHANNEL_WARNING: (
            "<tg-emoji emoji-id='5843843420468024653'>🔖</tg-emoji> <b>Сделка по каналу</b>\n\n"
            "<blockquote>Добавьте бота администратором канала и выдайте ему полные права, включая "
            "приглашение пользователей и назначение администраторов. Затем отправьте @username, ID канала "
            "или перешлите сообщение из канала.</blockquote>\n\n"
            "<blockquote>Покупатель вступит по инвайт-ссылке. После оплаты продавец вручную "
            "передаёт ему статус владельца. Бот автоматически проверяет статус и только после этого запускает выплату.</blockquote>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> <b>Не удаляйте бота из администраторов до завершения сделки!</b>"
        ),
        TextKey.DEAL_CHANNEL_INVALID: (
            "<tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> <b>Канал не прошёл проверку</b>\n\n"
            "<blockquote>{reason}</blockquote>\n\n"
            "Исправьте права и отправьте канал ещё раз."
        ),
        TextKey.DEAL_CHANNEL_VERIFIED: "Канал «{title}» проверен.",
        TextKey.DEAL_CHANNEL_INVITE_UNAVAILABLE: (
            "Не удалось создать безопасную ссылку для входа в канал. Оплата пока недоступна. "
            "Продавцу нужно проверить, что бот всё ещё является администратором с правом приглашать пользователей."
        ),
        TextKey.DEAL_PAY_BUTTON: "Оплатить в Tonkeeper",
        TextKey.DEAL_CHANNEL_JOIN_BUTTON: "Запросить доступ к каналу",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Создание оффера</b>\n\nУкажите, что вы предлагаете в сделке.\n\n"
            "Например:\n"
            "<blockquote>Цифровой товар, подарок, аккаунт или услуга и условия её оказания.</blockquote>"
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Создание сделки</b>\n\nВыберите валюту сделки <tg-emoji emoji-id='5908808657700655253'>👇</tg-emoji>",
        TextKey.DEAL_AMOUNT_PROMPT: "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Создание сделки</b>\n\nВведите сумму сделки.\n\nНапример: 5 или 12.5",
        TextKey.DEAL_AMOUNT_INVALID: "Введите положительное число.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "<blockquote><tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> Минимальная сумма сделки — {minimum} {currency} <tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji></blockquote>\n\n"
            "Комиссия сервиса добавляется к счёту; сетевой gas оплачивается отдельно."
        ),
        TextKey.DEAL_CREATED: (
            "<tg-emoji emoji-id='5879895758202735862'>🔒</tg-emoji> <b>Сделка #{deal_id} создана</b>\n\nДетали сделки:\n"
            "<blockquote>• Описание: {description}\n• Продавец получит: {amount} {currency}\n"
            "• Покупатель оплатит: {payment_amount} {currency}</blockquote>\n\n"
            "Для присоединения покупателя отправьте ему ссылку:\n{deep_link}"
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Отменить сделку",
        TextKey.DEAL_CONFIRM_BUTTON: "Завершить сделку",
        TextKey.DEAL_DELIVER_BUTTON: "Услуга оказана",
        TextKey.DEAL_DISPUTE_BUTTON: "Открыть спор",
        TextKey.DEAL_JOINED: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> <b>Сделка #{deal_id}</b>\n"
            "<tg-emoji emoji-id='5942877472163892475'>👤</tg-emoji> Вы покупатель.\n\n"
            "• Завершённых сделок продавца: {seller_deals}\n\n"
            "Детали сделки:\n"
            "<blockquote>• Код сделки: #{deal_id}\n"
            "• Описание: {description}</blockquote>\n\n"
            "• Адрес оплаты: {wallet_address}\n"
            "• Сумма к оплате: {amount} {currency}\n"
            "• Обязательный комментарий: {deal_id}\n\n"
            "<blockquote><tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> Пожалуйста, убедитесь, что при оплате указываете обязательный комментарий (memo) и точную сумму!</blockquote>\n\n"
            "После оплаты бот автоматически проверит перевод."
        ),
        TextKey.DEAL_NOT_FOUND: "Сделка не найдена.",
        TextKey.DEAL_FORBIDDEN: "У вас нет доступа к этой сделке.",
        TextKey.DEAL_ALREADY_CANCELLED: "Эту сделку уже нельзя отменить.",
        TextKey.DEAL_CANCELLED: "Сделка отменена.",
        TextKey.DEAL_LIST_EMPTY: "Здесь пока ничего нет",
        TextKey.DEAL_LIST_CAPTION: "<b>Мои сделки:</b>",
        TextKey.DEAL_CARD: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> <b>Сделка #{deal_id}</b>\n\nДетали сделки:\n"
            "<blockquote>• Описание: {description}\n• Продавец получил: {amount} {currency}\n"
            "• Покупатель оплатит: {payment_amount} {currency}</blockquote>\n\n"
            "Продавец:\n{seller}\n\nПокупатель:\n{buyer}{channel_details}\n\n"
            "Статус: {status}"
        ),
        TextKey.DEAL_PAID_BUYER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата найдена и подтверждена!</b>\n"
            "Ваш платеж по сделке #{deal_id} успешно обработан.\n\n"
            "Транзакция:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "Детали сделки:\n"
            "<blockquote>• Описание: {description}\n"
            "• Продавец: {seller}</blockquote>\n\n"
            "Ожидайте подтверждения оказания услуги от продавца."
        ),
        TextKey.DEAL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата подтверждена!</b>\n"
            "Покупатель оплатил сделку #{deal_id}\n\n"
            "Транзакция:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "Детали сделки:\n"
            "<blockquote>• Описание: {description}\n"
            "• Покупатель: {buyer}</blockquote>\n\n"
            "<tg-emoji emoji-id='5985780596268339498'>🤖</tg-emoji> Средства зачислены на кошелёк бота.\n"
            "Теперь вы можете приступить к оказанию услуги. Не забудьте нажать кнопку ниже!"
        ),
        TextKey.DEAL_CHANNEL_PAID_BUYER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата найдена и подтверждена!</b>\n"
            "Ваш платеж по сделке #{deal_id} успешно обработан.\n\n"
            "Транзакция:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> Вступите в канал по кнопке сделки и дождитесь, пока продавец вручную передаст вам статус владельца. Бот проверит это автоматически."
        ),
        TextKey.DEAL_CHANNEL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата подтверждена!</b>\n"
            "Покупатель оплатил сделку #{deal_id}\n\n"
            "Транзакция:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> Вручную передайте ему статус владельца в настройках Telegram и не удаляйте бота из администраторов. После статуса creator бот автоматически запустит выплату."
        ),
        TextKey.DEAL_RELEASE_ACCEPTED: (
            "<b>Завершение сделки и выплаты:</b>\n"
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Сделка успешно завершена!\n\n"
            "Детали сделки:\n"
            "<blockquote>• Описание: {description}\n"
            "• Продавец получил: {seller_amount} {currency}\n"
            "• Покупатель оплатил: {payment_amount} {currency}</blockquote>\n\n"
            "<tg-emoji emoji-id='5843908536467198016'>🔄</tg-emoji> Выплата продавцу обрабатывается.\n"
            "Он получит уведомление после завершения транзакции."
        ),
        TextKey.DEAL_CONFIRMED: "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Завершена",
        TextKey.DEAL_WAIT_WALLET: "У продавца не привязан кошелек для выплаты.",
        TextKey.DEAL_BUYER_WALLET_REQUIRED: (
            "Перед вступлением в сделку привяжите TON-кошелёк в разделе «Мой кошелёк». "
            "Он нужен как безопасный адрес возврата."
        ),
        TextKey.DEAL_PAYOUT_BLOCKED: (
            "Выплата остановлена до отправки: на кошельке гаранта недостаточно gas. "
            "Средства остаются у гаранта; обратитесь в поддержку."
        ),
        TextKey.DEAL_DELIVERED: (
            "<b>Исполнение и доставка:</b>\n"
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Услуга отмечена как оказанная!\n\n"
            "Покупатель получил уведомление и может подтвердить получение."
        ),
        TextKey.DEAL_DELIVERY_NOTICE: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Продавец оказал услугу!\n\n"
            "Продавец подтвердил, что оказал услугу по сделке:\n"
            "<blockquote>• Код сделки: #{deal_id}\n"
            "• Описание: {description}\n"
            "• Сумма к оплате: {payment_amount} {currency}</blockquote>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>⚠</tg-emoji>️</tg-emoji> Пожалуйста, проверьте качество выполненной работы.\n\n"
            "<tg-emoji emoji-id='5881702736843511327'><tg-emoji emoji-id='5881702736843511327'>ℹ</tg-emoji>️</tg-emoji> После вашего подтверждения средства будут переведены продавцу.\n"
            "Если в течение 1 часа вы не подтвердите получение товара и не откроете спор, сделка будет завершена автоматически."
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
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Сделка успешно завершена!</b>\n<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>Выплата получена!</b>\n\nДетали сделки:\n"
            "<blockquote>• Описание: {description}\n"
            "• Сумма: {amount} {currency}\n"
            "• Кошелек: {wallet}</blockquote>\n\n"
            "Транзакция:\n<a href=\"{transaction_url}\"><tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> Посмотреть в TON Viewer</a>\n\n"
            "Спасибо за использование нашего сервиса! <tg-emoji emoji-id='5908808657700655253'>🐱</tg-emoji>"
        ),
        TextKey.SETTINGS_CAPTION: "<tg-emoji emoji-id='5877260593903177342'><tg-emoji emoji-id='5877260593903177342'>⚙</tg-emoji>️</tg-emoji> <b>Настройки</b>",
        TextKey.SETTINGS_REFERRALS: "Рефералы",
        TextKey.SETTINGS_LANGUAGE: "Язык",
        TextKey.SETTINGS_SUPPORT: "Поддержка",
        TextKey.LANGUAGE_PROMPT: (
            "<tg-emoji emoji-id='5449408995691341691'>🇷🇺</tg-emoji> ← Выберите язык бота прежде чем начать пользоваться.\n\n"
            "<tg-emoji emoji-id='5202021044105257611'>🇺🇸</tg-emoji> ← Choose the bot's language before you start using it."
        ),
        TextKey.LANGUAGE_SAVED: (
            "<tg-emoji emoji-id='5776375003280838798'>🎉</tg-emoji> <b>Язык успешно установлен!</b>\n\n"
            "<blockquote>Нажмите на кнопку ниже чтобы перейти в главное меню. <tg-emoji emoji-id='5908808657700655253'>👇</tg-emoji></blockquote>"
        ),
        TextKey.SUPPORT_TEXT: "<tg-emoji emoji-id='5967411695453213733'>🛟</tg-emoji> <b>Поддержка</b>\n\nПо вопросам и спорам напишите {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "<tg-emoji emoji-id='5942877472163892475'>👥</tg-emoji> <b>Рефералы</b>\n\nДетали:\n"
            "<blockquote>• Реферальный процент: {rate} %\n"
            "• Приглашено пользователей: {count}</blockquote>\n\n"
            "Баланс:\n"
            "<blockquote>• GRAM: {earned_ton}\n"
            "• USDT ( <tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> ): {earned_usdt}</blockquote>\n\n"
            "Ваша реферальная ссылка:\n<code>{link}</code>"
        ),
        TextKey.BACK_BUTTON: "Назад",
        TextKey.MAIN_MENU_BUTTON: "Главное меню",
        TextKey.FAQ_CAPTION: (
            "<tg-emoji emoji-id='5778184941154078090'>📚</tg-emoji> <b>Помощь и часто задаваемые вопросы</b>\n\n"
            "Как использовать сервис:\n"
            "<blockquote>1. Добавьте свой TON-кошелёк в разделе «Мой кошелёк».\n"
            "2. Создайте сделку или присоединитесь к существующей.\n"
            "3. Покупатель переводит средства — они замораживаются на escrow.\n"
            "4. После оказания услуги покупатель подтверждает — деньги автоматически уходят продавцу.</blockquote>\n\n"
            "Как долго заморожены деньги?\n"
            "<blockquote>До подтверждения покупателем или отмены сделки.</blockquote>\n\n"
            "Что если продавец не выполнил работу?\n"
            "<blockquote>Вы можете отменить сделку и вернуть средства до подтверждения.</blockquote>\n\n"
            "Сколько стоит комиссия?\n"
            "<blockquote>Фиксировано 1% от суммы сделки.</blockquote>\n\n"
            "Можно ли торговать криптовалютой, товарами или услугами?\n"
            "<blockquote>Да, любые сделки между двумя пользователями.</blockquote>\n\n"
            "Как работает реферальная система?\n"
            "<blockquote>Вы получаете 10% от комиссии сервиса по завершённым сделкам приглашённых пользователей.</blockquote>\n\n"
            "Нужна помощь? Свяжитесь с поддержкой: {support_username}"
        ),
        TextKey.DOCUMENTS_CAPTION: "<tg-emoji emoji-id='6028226658543082010'>📄</tg-emoji> <b>Документы</b>\n\nВыберите документ:",
        TextKey.PRIVACY_BUTTON: "Политика конфиденциальности",
        TextKey.TERMS_BUTTON: "Пользовательское соглашение",
        TextKey.SERVICE_DESCRIPTION_BUTTON: "Описание и условия сервиса",
        TextKey.LANG_RU: "Русский",
        TextKey.LANG_EN: "English",
        TextKey.COMPLETED_DEAL_FEED: (
            "<b>Сделка:</b> <code>#{deal_id}</code>\n\n"
            "Детали сделки:\n"
            "<blockquote><b>• Описание:</b> {description}\n"
            "<b>• Сумма:</b> {amount} {currency}</blockquote>\n\n"
            "@grntrobot"
        ),
    },
    Language.EN: {
        TextKey.MAIN_MENU_CAPTION: (
            "<b>For those who value speed and security.</b> Make deals without unnecessary intermediaries.\n\n"
            "<tg-emoji emoji-id='5985780596268339498'>🤖</tg-emoji> <b>Technology:</b> Direct TON × Telegram integration\n\n"
            "<tg-emoji emoji-id='5908808657700655253'>✋</tg-emoji> <b>Security:</b> Assets are frozen until conditions are completed\n\n"
            "<tg-emoji emoji-id='5778139491810155937'>📊</tg-emoji> <b>Transparency:</b> Fixed 1% fee\n\n<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>Reviews:</b> <a href=\"https://t.me/grnthub/4\">@grnthub</a>"
        ),
        TextKey.MENU_WALLET: "My wallet",
        TextKey.MENU_CREATE_DEAL: "Create deal",
        TextKey.MENU_MY_DEALS: "My deals",
        TextKey.MENU_SETTINGS: "Settings",
        TextKey.MENU_FAQ: "Questions",
        TextKey.MENU_DOCUMENTS: "Documents",
        TextKey.WALLET_CAPTION: (
            "<tg-emoji emoji-id='5769403330761593044'>💵</tg-emoji> <b>Wallet</b>\n\n<a href=\"{wallet_url}\">{wallet_short}</a>\n\n"
            "<b>Full address:</b> <code>{wallet}</code>"
        ),
        TextKey.WALLET_EMPTY: "<tg-emoji emoji-id='5769403330761593044'>💵</tg-emoji> <b>My wallet</b>\n\nSelect or add your wallet below:",
        TextKey.WALLET_ADD: "Add wallet",
        TextKey.WALLET_CHANGE: "Change wallet",
        TextKey.WALLET_DELETE: "Delete wallet",
        TextKey.WALLET_DELETED: "Wallet deleted.",
        TextKey.WALLET_PROMPT: "<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>My wallet</b>\n\nSend the TON address you want to link to your profile.",
        TextKey.WALLET_ACTIVE_PROMPT: (
            "<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>My wallet</b>\n\nCurrent address:\n<code>{wallet}</code>\n\n"
            "Want to change it? Send a new address."
        ),
        TextKey.WALLET_SAVED: "Wallet saved: {wallet}",
        TextKey.WALLET_INVALID: "This does not look like a TON address. Please try again.",
        TextKey.WALLET_OPEN: "Open wallet",
        TextKey.DEAL_CREATE_INTRO: "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Create a deal</b>\n\nChoose the deal type <tg-emoji emoji-id='5908808657700655253'>👇</tg-emoji>",
        TextKey.DEAL_TYPE_GIFTS: "Offer",
        TextKey.DEAL_TYPE_OFFER: "Offer",
        TextKey.DEAL_TYPE_CHANNEL: "Channel",
        TextKey.DEAL_TYPE_ACCOUNT: "Offer",
        TextKey.DEAL_CHANNEL_WARNING: (
            "<tg-emoji emoji-id='5967411695453213733'>📢</tg-emoji> <b>Channel deal</b>\n\nAdd the bot as a channel administrator with <b>full rights</b>, including inviting users "
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
        TextKey.DEAL_CHANNEL_JOIN_BUTTON: "Request channel access",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Create an offer</b>\n\nDescribe what you offer in the deal.\n\n"
            "<blockquote>Example: a digital item, gift, account, service, and its delivery terms.</blockquote>"
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Create a deal</b>\n\nChoose the deal currency <tg-emoji emoji-id='5908808657700655253'>👇</tg-emoji>",
        TextKey.DEAL_AMOUNT_PROMPT: "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Create a deal</b>\n\nEnter the deal amount.\nExample: <code>5</code> or <code>12.5</code>",
        TextKey.DEAL_AMOUNT_INVALID: "Please enter a positive number.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "The minimum deal amount is {minimum} {currency}. "
            "The service fee is added to the invoice; network gas is paid separately."
        ),
        TextKey.DEAL_CREATED: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Deal #{deal_id} created</b>\n\n<b>Type:</b> {deal_type}\n<b>Description:</b> {description}\n"
            "<b>Seller receives:</b> {amount} {currency}\n<b>Buyer pays:</b> {payment_amount} {currency}\n\n"
            "<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>Escrow address:</b>\n<code>{wallet_address}</code>\n"
            "<tg-emoji emoji-id='6028226658543082010'>📝</tg-emoji> <b>Required comment:</b> <code>{deal_id}</code>\n"
            "<tg-emoji emoji-id='5985630530111020079'>🔗</tg-emoji> <a href=\"{deep_link}\">Buyer link</a>\n\n"
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
            "<tg-emoji emoji-id='5967389567781703494'>💼</tg-emoji> <b>Deal #{deal_id}</b>\n\n<tg-emoji emoji-id='5942877472163892475'>👤</tg-emoji> You are the buyer.\n\n"
            "• Seller completed deals: {seller_deals}\n\n<b>Deal details:</b>\n"
            "• Deal code: #{deal_id}\n• Description: {description}\n\n"
            "<b>Payment address:</b>\n<code>{wallet_address}</code>\n\n"
            "<b>Amount due:</b>\n{amount} {currency}\n\n"
            "<b>Required comment:</b>\n<code>{deal_id}</code>\n\n"
            "<blockquote><tg-emoji emoji-id='5775887550262546277'><tg-emoji emoji-id='5775887550262546277'>‼</tg-emoji>️</tg-emoji> Use the exact amount and required comment (memo).</blockquote>\n"
            "The bot verifies payment automatically. A refund returns D; the 1% service fee is retained."
        ),
        TextKey.DEAL_NOT_FOUND: "Deal not found.",
        TextKey.DEAL_FORBIDDEN: "You do not have access to this deal.",
        TextKey.DEAL_ALREADY_CANCELLED: "This deal can no longer be cancelled.",
        TextKey.DEAL_CANCELLED: "Deal cancelled.",
        TextKey.DEAL_LIST_EMPTY: "Nothing here yet",
        TextKey.DEAL_LIST_CAPTION: "<b>My deals:</b>",
        TextKey.DEAL_CARD: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> <b>Deal #{deal_id}</b>\n\n<b>Deal details:</b>\n"
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
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Channel deal #{deal_id} payment is confirmed and held by the guarant.\nTransaction:\n{transaction_url}\n\n"
            "Join through the deal button and wait for the seller "
            "to transfer ownership. The bot verifies it automatically."
        ),
        TextKey.DEAL_CHANNEL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> The buyer paid channel deal #{deal_id}. Transfer ownership manually in Telegram and keep the bot as administrator. "
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
            "<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>Payout received!</b>\n\n<b>Deal details:</b>\n• Description: {description}\n"
            "• Amount: {amount} {currency}\n• Status: <tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Successfully completed\n"
            "• Wallet: <code>{wallet}</code>\n\n"
            "<tg-emoji emoji-id='5985630530111020079'>🔗</tg-emoji> <a href=\"{transaction_url}\">View transaction</a>\n\nThank you for using our service! <tg-emoji emoji-id='5908808657700655253'>🙏</tg-emoji>"
        ),
        TextKey.SETTINGS_CAPTION: "<tg-emoji emoji-id='5877260593903177342'><tg-emoji emoji-id='5877260593903177342'>⚙</tg-emoji>️</tg-emoji> <b>Settings</b>",
        TextKey.SETTINGS_REFERRALS: "Referrals",
        TextKey.SETTINGS_LANGUAGE: "Language",
        TextKey.SETTINGS_SUPPORT: "Support",
        TextKey.LANGUAGE_PROMPT: (
            "<tg-emoji emoji-id='5449408995691341691'>🇷🇺</tg-emoji> ← Выберите язык бота прежде чем начать пользоваться.\n\n"
            "<tg-emoji emoji-id='5202021044105257611'>🇺🇸</tg-emoji> ← Choose the bot's language before you start using it."
        ),
        TextKey.LANGUAGE_SAVED: (
            "<tg-emoji emoji-id='5776375003280838798'>🎉</tg-emoji> <b>Language successfully set!</b>\n\n"
            "<blockquote>Press the button below to open the main menu. <tg-emoji emoji-id='5908808657700655253'>👇</tg-emoji></blockquote>"
        ),
        TextKey.SUPPORT_TEXT: "<tg-emoji emoji-id='5967411695453213733'>🛟</tg-emoji> <b>Support</b>\n\nFor support or disputes, contact {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "<tg-emoji emoji-id='5942877472163892475'>👥</tg-emoji> <b>Referral program</b>\n\n<b>Reward:</b> {rate}% of the service fee from completed referred deals\n"
            "<b>Invited:</b> {count}\n<b>GRAM balance:</b> {earned_ton}\n<b>USDT balance:</b> {earned_usdt}\n\n"
            "<tg-emoji emoji-id='5985630530111020079'>🔗</tg-emoji> <b>Your link:</b>\n<code>{link}</code>\n\n"
            "Withdrawals go to the linked address. Exchanges, custodial services and third-party "
            "wallets may require extra metadata and are used at your own risk."
        ),
        TextKey.BACK_BUTTON: "Back",
        TextKey.MAIN_MENU_BUTTON: "Main menu",
        TextKey.FAQ_CAPTION: (
            "<tg-emoji emoji-id='5778184941154078090'>📚</tg-emoji> <b>Help and frequently asked questions</b>\n\n"
            "Add a TON wallet, create or join a deal, fund escrow, and confirm delivery to release funds.\n\n"
            "<b>How long are funds frozen?</b> Until buyer confirmation or cancellation.\n\n"
            "<b>Service fee:</b> fixed 1%.\n\n<b>Disputes:</b> contact {support_username}.\n\n"
            "Referral reward is 10% of the service fee generated by completed deals of invited users."
        ),
        TextKey.DOCUMENTS_CAPTION: "<tg-emoji emoji-id='6028226658543082010'>📄</tg-emoji> <b>Documents</b>\n\nChoose a document:",
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
