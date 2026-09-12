from app.core.enums import Language
from app.locales.keys import TextKey


TEXTS: dict[Language, dict[TextKey, str]] = {
    Language.RU: {
        TextKey.MAIN_MENU_CAPTION: (
            "<b>Просто сделки. Остальное — на нас.</b>\n\n"
            "<b>Главное о сервисе:</b>\n"
            "<blockquote expandable>"
            "<tg-emoji emoji-id='5778139491810155937'>💎</tg-emoji> <b>Начало сделки:</b>\n"
            "Опишите условия сделки в чате с гарантом.\n\n"
            "<tg-emoji emoji-id='5931415565955503486'>🤖</tg-emoji> <b>Фиксация средств:</b>\n"
            "Бот удерживает активы до выполнения оговоренных условий.\n\n"
            "<tg-emoji emoji-id='6028530359975548369'>💎</tg-emoji> <b>Выплата средств:</b>\n"
            "После подтверждения обеими сторонами средства переводятся получателю.\n\n"
            "<tg-emoji emoji-id='6028226658543082010'>🔨</tg-emoji> <b>Важно:</b>\n"
            "<b>GRNT выступает нейтральным гарантом и сопровождает только сделки, соответствующие нашим правилам и политике Telegram.</b>\n\n"
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>1%:</b>\n"
            "Фиксированная комиссия за завершённую сделку."
            "</blockquote>\n\n"
            "<tg-emoji emoji-id='5967412305338568701'>📅</tg-emoji> <b>Публичная история:</b> "
            "<a href='https://t.me/grnthub/4'>@grnthub</a>"
        ),
        TextKey.MENU_WALLET: "Мой кошелек",
        TextKey.MENU_CREATE_DEAL: "Создать сделку",
        TextKey.MENU_MY_DEALS: "Мои сделки",
        TextKey.MENU_SETTINGS: "Настройки",
        TextKey.MENU_FAQ: "Помощь и FAQ",
        TextKey.MENU_DOCUMENTS: "Документы",
        TextKey.MENU_CREATE_DESK: "Создать объявление",
        TextKey.DESK_KIND_PROMPT: (
            "<tg-emoji emoji-id='5839116473951328489'>📌</tg-emoji> <b>Создание объявления</b>\n\n"
            "Выберите из следующего:\n"
            "<blockquote>WTS — для продажи/оказания услуги и тд.\n\n"
            "WTB — для покупки/поиска услуги и тд.</blockquote>"
        ),
        TextKey.DESK_DESCRIPTION_PROMPT: (
            "<tg-emoji emoji-id='5839116473951328489'>📌</tg-emoji> <b>Создание объявления</b>\n\n"
            "Укажите, что вы предлагаете в объявлении.\n\n"
            "Например:\n<blockquote>Цифровой товар, подарок, аккаунт или услуга и условия её оказания.</blockquote>"
        ),
        TextKey.DESK_DESCRIPTION_PREVIEW: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\n"
            "<b>Детали сделки:</b>\n<blockquote>• Описание:\n{description}</blockquote>\n\n"
            "Проверьте описание. Чтобы исправить его, просто отправьте новый текст."
        ),
        TextKey.DESK_DEAL_CURRENCY_PROMPT: "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\nВыберите валюту для сделки в объявлении:",
        TextKey.DESK_AMOUNT_PROMPT: "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\nВведите сумму сделки или нажмите кнопку Оффер, если цена согласовывается в DM.\n\nНапример: 5 или 12.5",
        TextKey.DESK_PAYMENT_CURRENCY_PROMPT: "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\nВыберите валюту для оплаты публикации:",
        TextKey.DESK_PAYMENT_INVOICE: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\n"
            "Чтобы опубликовать сообщение в разделе Desk, отправьте точную сумму на адрес гаранта.\n\n"
            "<b>Адрес:</b>\n<code>{wallet}</code>\n\n<b>Сумма:</b> {fee} {currency}\n"
            "<b>Обязательный комментарий:</b> <code>{username}</code>\n\n"
            "<blockquote>Комментарий можно указать с @ или без него. Оплата действует 15 минут.</blockquote>"
        ),
        TextKey.DESK_CREATED: (
            "<tg-emoji emoji-id='5875206779196935950'>📅</tg-emoji> <b>Объявление</b> <code>#{listing_id}</code> <b>создано</b>\n\n"
            "<b>Детали объявления:</b>\n<blockquote>• Описание:\n{description}\n\n• Цена: {price}</blockquote>"
        ),
        TextKey.DESK_EXPIRED: "Время оплаты объявления истекло. Создайте его заново.",
        TextKey.DESK_USERNAME_REQUIRED: "Для публикации объявления у профиля Telegram должен быть @username.",
        TextKey.DESK_INVALID_AMOUNT: "Введите положительное число, например 5 или 12.5.",
        TextKey.OTC_OFFER_PROMPT: (
            "<tg-emoji emoji-id='5775887550262546277'>❗️</tg-emoji> <b>Создать OTC-предложение</b>\n\n"
            "<b>Детали:</b>\n"
            "<blockquote><b>Item:</b> {item}\n<b>Price:</b> {price}</blockquote>\n\n"
            "<b>Введите сумму предложения в GRAM:</b>"
        ),
        TextKey.OTC_OFFER_SENT: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji>"
            "Ваше предложение <b>{amount} GRAM</b> отправлено владельцу. "
            "Ожидайте принятия решения."
        ),
        TextKey.OTC_OFFER_INCOMING: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>Новое OTC-предложение</b>\n\n"
            "<b>Детали:</b>\n"
            "<blockquote><b>Item:</b> {item}\n"
            "<b>Amount:</b> {amount} GRAM\n"
            "<b>Buyer:</b> {buyer}</blockquote>\n\n"
            "Бот только связывает стороны.\n"
            "Расчёты происходят напрямую между пользователями.\n\n"
            "<b>Примите или отклоните предложение:</b>"
        ),
        TextKey.OTC_OFFER_RESULT: (
            "<tg-emoji emoji-id='5879785854284599288'>ℹ️</tg-emoji> <b>Статус OTC-предложения</b>\n\n"
            "<b>Детали:</b>\n"
            "<blockquote><b>Название:</b> {item}\n"
            "<b>Сумма предложения:</b> {amount} GRAM</blockquote>\n\n"
            "<b>Статус:</b> {status}\n\n"
            "Свяжитесь со второй стороной для совершения сделки.\n"
            "Расчёт суммы сделки происходит напрямую между пользователями.\n\n"
            "Бот не переводит GRAM, NFT или другие активы — он только связывает стороны."
        ),
        TextKey.OTC_OFFER_UNAVAILABLE: (
            "Объявление не существует, уже не активно или принадлежит вам."
        ),
        TextKey.OTC_OFFER_INVALID_AMOUNT: (
            "Введите положительную сумму с числом знаков после запятой не более 9."
        ),
        TextKey.OTC_OFFER_COOLDOWN: (
            "Новое предложение можно отправить через {seconds} сек."
        ),
        TextKey.OTC_OFFER_ALREADY_RESOLVED: (
            "Предложение уже обработано или недоступно."
        ),
        TextKey.OTC_OFFER_ACCEPT_BUTTON: "Принять",
        TextKey.OTC_OFFER_DECLINE_BUTTON: "Отклонить",
        TextKey.OTC_OFFER_PROFILE_BUTTON: "Профиль",
        TextKey.WALLET_PROMPT: "<tg-emoji emoji-id='5769403330761593044'>👛</tg-emoji> <b>Мой кошелёк</b>\n\nОтправьте TON-адрес, который нужно привязать к профилю.",
        TextKey.WALLET_ACTIVE_PROMPT: (
            "<tg-emoji emoji-id='5769403330761593044'>👛</tg-emoji> <b>Мой кошелёк</b>\n\n<b>Текущий адрес:</b>\n"
            "<blockquote><a href=\"{wallet_url}\">{wallet_short}</a></blockquote>\n\n"
            "Хотите изменить? Отправьте новый адрес."
        ),
        TextKey.WALLET_SAVED: "Кошелёк сохранён:\n<blockquote><code>{wallet}</code></blockquote>",
        TextKey.WALLET_INVALID: "Похоже, это не TON-адрес. Проверьте формат и отправьте ещё раз.",
        TextKey.DEAL_CREATE_INTRO: "<tg-emoji emoji-id='5956561916573782596'>💬</tg-emoji> <b>Создание сделки</b>\n\nВыберите тип сделки:",
        TextKey.DEAL_TYPE_OFFER: "Оффер",
        TextKey.DEAL_TYPE_CHANNEL: "Канал",
        TextKey.DEAL_CHANNEL_WARNING: (
            "<tg-emoji emoji-id='5839116473951328489'>⭐️</tg-emoji> <b>Сделка по каналу</b>\n\n"
            "<blockquote>Добавьте бота администратором канала и выдайте ему полные права, включая "
            "приглашение пользователей и назначение администраторов. Затем отправьте @username, ID канала "
            "или перешлите сообщение из канала.</blockquote>\n\n"
            "<blockquote>Покупатель вступит по инвайт-ссылке. После оплаты продавец вручную "
            "передаёт ему статус владельца. Бот автоматически проверяет статус и только после этого запускает выплату.</blockquote>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> <b>Не удаляйте бота из администраторов до завершения сделки!</b>"
        ),
        TextKey.DEAL_CHANNEL_INVALID: (
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> <b>Канал не прошёл проверку</b>\n\n"
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
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>Создание оффера</b>\n\nУкажите, что вы предлагаете в сделке.\n\n"
            "Например:\n"
            "<blockquote>Цифровой товар, подарок, аккаунт или услуга и условия её оказания.</blockquote>"
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "<tg-emoji emoji-id='5956561916573782596'>💬</tg-emoji> <b>Создание сделки</b>\n\nВыберите валюту сделки:",
        TextKey.DEAL_AMOUNT_PROMPT: "<tg-emoji emoji-id='5956561916573782596'>💬</tg-emoji> <b>Создание сделки</b>\n\nВведите сумму сделки.\n\nНапример: 5 или 12.5",
        TextKey.DEAL_AMOUNT_INVALID: "Введите положительное число.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "<blockquote><tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Минимальная сумма сделки — {minimum} {currency} <tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji></blockquote>\n\n"
            "Комиссия сервиса добавляется к счёту; сетевой gas оплачивается отдельно."
        ),
        TextKey.DEAL_CREATED: (
            "<tg-emoji emoji-id='5879895758202735862'>🔒</tg-emoji> <b>Сделка</b> <code>#{deal_id}</code> <b>создана</b>\n\nДетали сделки:\n"
            "<blockquote>• Описание: {description}\n• Продавец получит: {amount} {currency}\n"
            "• Покупатель оплатит: {payment_amount} {currency}</blockquote>\n\n"
            "Для присоединения покупателя отправьте ему ссылку:\n{deep_link}"
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Отменить сделку",
        TextKey.DEAL_CONFIRM_BUTTON: "Завершить сделку",
        TextKey.DEAL_DELIVER_BUTTON: "Услуга оказана",
        TextKey.DEAL_DISPUTE_BUTTON: "Открыть спор",
        TextKey.DEAL_JOINED: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> <b>Сделка</b> <code>#{deal_id}</code>\n"
            "<tg-emoji emoji-id='5942877472163892475'>👤</tg-emoji> Вы покупатель.\n\n"
            "Завершённых сделок продавца: {seller_deals}\n\n"
            "<b>Детали сделки:</b>\n"
            "<blockquote><b>• Код сделки:</b> <code>#{deal_id}</code>\n"
            "<b>• Описание:</b> {description}</blockquote>\n\n"
            "<b>• Адрес оплаты:</b> <code>{wallet_address}</code>\n\n"
            "<b>• Сумма к оплате:</b> <code>{amount}</code> {currency}\n\n"
            "<b>• Комментарий (необязательно):</b> <code>{deal_id}</code>\n\n"
            "<blockquote><tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Отправьте точную сумму на указанный адрес. Комментарий можно не указывать.</blockquote>\n\n"
            "<b>После оплаты бот автоматически проверит перевод.</b>"
        ),
        TextKey.DEAL_NOT_FOUND: "Сделка не найдена.",
        TextKey.DEAL_FORBIDDEN: "У вас нет доступа к этой сделке.",
        TextKey.DEAL_ALREADY_CANCELLED: "Эту сделку уже нельзя отменить.",
        TextKey.DEAL_CANCELLED: "Сделка отменена.",
        TextKey.DEAL_LIST_EMPTY: "<tg-emoji emoji-id='5967548335542767952'>📋</tg-emoji> <b>Мои сделки</b>\n\nЗдесь пока ничего нет",
        TextKey.DEAL_LIST_CAPTION: "<tg-emoji emoji-id='5967548335542767952'>📋</tg-emoji> <b>Мои сделки:</b>",
        TextKey.DEAL_CARD: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> "
            "<b>Сделка</b> <code>#{deal_id}</code>\n\n"
            "<b>Детали:</b>\n"
            "<blockquote>• Описание: {description}\n"
            "• Продавец {seller_amount_verb}: {amount} {currency}\n"
            "• Покупатель {buyer_amount_verb}: {payment_amount} {currency}</blockquote>\n\n"
            "<b>Продавец:</b>\n{seller}\n\n"
            "<b>Покупатель:</b>\n{buyer}{channel_details}\n\n"
            "<b>Статус:</b> {status}"
        ),
        TextKey.DEAL_PAID_BUYER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата найдена и подтверждена!</b>\n\n"
            "Ваш платеж по сделке <code>#{deal_id}</code> успешно обработан.\n\n"
            "<b>Транзакция:</b>\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "<b>Детали сделки:</b>\n"
            "<blockquote><b>• Описание:</b> {description}\n"
            "<b>• Продавец:</b> {seller}</blockquote>\n\n"
            "<b>Ожидайте подтверждения оказания услуги от продавца.</b>"
        ),
        TextKey.DEAL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата подтверждена!</b>\n\n"
            "Покупатель оплатил сделку <code>#{deal_id}</code>\n\n"
            "<b>Транзакция:</b>\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "<b>Детали сделки:</b>\n"
            "<blockquote><b>• Описание:</b> {description}\n"
            "<b>• Покупатель:</b> {buyer}</blockquote>\n\n"
            "<tg-emoji emoji-id='5985780596268339498'>🤖</tg-emoji> Средства зачислены на кошелёк бота.\n"
            "<b>Теперь вы можете приступить к оказанию услуги. Не забудьте нажать кнопку ниже!</b>"
        ),
        TextKey.DEAL_CHANNEL_PAID_BUYER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата найдена и подтверждена!</b>\n\n"
            "Ваш платеж по сделке <code>#{deal_id}</code> успешно обработан.\n\n"
            "<b>Транзакция:</b>\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Вступите в канал по кнопке сделки и дождитесь, пока продавец вручную передаст вам статус владельца. Бот проверит это автоматически."
        ),
        TextKey.DEAL_CHANNEL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Оплата подтверждена!</b>\n\n"
            "Покупатель оплатил сделку <code>#{deal_id}</code>\n\n"
            "<b>Транзакция:</b>\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">Посмотреть в TON Viewer</a>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Вручную передайте ему статус владельца в настройках Telegram и не удаляйте бота из администраторов. После статуса creator бот автоматически запустит выплату."
        ),
        TextKey.DEAL_RELEASE_ACCEPTED: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Сделка успешно завершена!</b>\n\n"
            "<b>Детали сделки:</b>\n"
            "<blockquote><b>• Описание:</b> {description}\n"
            "<b>• Продавец получил:</b> {seller_amount} {currency}\n"
            "<b>• Покупатель оплатил:</b> {payment_amount} {currency}</blockquote>\n\n"
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
            "Выплата остановлена до отправки: на кошельке гаранта недостаточно gas."
            "Средства остаются у гаранта; обратитесь в поддержку."
        ),
        TextKey.DEAL_DELIVERED: (
            "<b>Исполнение и доставка:</b>\n"
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Услуга отмечена как оказанная!\n\n"
            "Покупатель получил уведомление и может подтвердить получение."
        ),
        TextKey.DEAL_DELIVERY_NOTICE: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Продавец оказал услугу!\n\n"
            "<b>Продавец подтвердил, что оказал услугу по сделке:</b>\n"
            "<blockquote><b>• Код сделки:</b> <code>#{deal_id}</code>\n"
            "<b>• Описание:</b> {description}\n"
            "<b>• Сумма к оплате:</b> {payment_amount} {currency}</blockquote>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Пожалуйста, проверьте качество выполненной работы.\n\n"
            "<blockquote><tg-emoji emoji-id='6028435952299413210'>ℹ️</tg-emoji> После вашего подтверждения средства будут переведены продавцу.</blockquote>\n\n"
            "Если в течение 1 часа вы не подтвердите получение товара и не откроете спор, <b>сделка будет завершена автоматически.</b>"
        ),
        TextKey.DEAL_DISPUTE_PROMPT: (
            "Опишите проблему одним сообщением (10–1000 символов). Скриншоты в боте не хранятся; "
            "при необходимости отправьте их напрямую в службу поддержки."
        ),
        TextKey.DEAL_DISPUTE_INVALID: "Описание должно содержать от 10 до 1000 символов.",
        TextKey.DEAL_DISPUTE_CREATED: (
            "Спорный тикет создан. Средства заморожены на кошельке гаранта."
            "Для разбора напишите в службу поддержки, опишите проблему и укажите ID сделки."
        ),
        TextKey.DEAL_REFUNDED: "Возврат покупателю подтверждён сетью TON.",
        TextKey.DEAL_CANCELLED_BY_SELLER: "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Сделка отменена продавцом\n\n<b>Код сделки:</b> <code>#{deal_id}</code>",
        TextKey.DEAL_PAYOUT_RECEIVED: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Сделка успешно завершена!</b>\n<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>Выплата получена!</b>\n\nДетали сделки:\n"
            "<blockquote><b>• Описание:</b> {description}\n"
            "<b>• Сумма:</b> <code>{amount}</code> {currency}\n"
            "<b>• Кошелек:</b> <code>{wallet}</code></blockquote>\n\n"
            "<b>Транзакция:</b>\n<a href=\"{transaction_url}\"><tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> Посмотреть в TON Viewer</a>\n\n"
            "<b>Спасибо за использование нашего сервиса!</b> <tg-emoji emoji-id='5908808657700655253'>🐱</tg-emoji>"
        ),
        TextKey.SETTINGS_CAPTION: "<tg-emoji emoji-id='5877260593903177342'>⚙️</tg-emoji> <b>Настройки</b>",
        TextKey.SETTINGS_REFERRALS: "Рефералы",
        TextKey.SETTINGS_LANGUAGE: "Язык",
        TextKey.SETTINGS_SUPPORT: "Поддержка",
        TextKey.LANGUAGE_PROMPT: (
            "<tg-emoji emoji-id='5449408995691341691'>🇷🇺</tg-emoji> ← Выберите язык бота прежде чем начать пользоваться.\n\n"
            "<tg-emoji emoji-id='5202021044105257611'>🇺🇸</tg-emoji> ← Choose the bot's language before you start using it."
        ),
        TextKey.LANGUAGE_SAVED: "<tg-emoji emoji-id='5776375003280838798'>🎉</tg-emoji> <b>Язык успешно установлен!</b>",
        TextKey.SUPPORT_TEXT: "<tg-emoji emoji-id='5967411695453213733'>🛟</tg-emoji> <b>Поддержка</b>\n\nПо вопросам и спорам напишите {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "<tg-emoji emoji-id='5942877472163892475'>👥</tg-emoji> <b>Рефералы</b>\n\n<b>Детали:</b>\n"
            "<blockquote>• <b>Уровень:</b> {level}\n"
            "• <b>Реферальный процент:</b> {rate}%\n"
            "• <b>Реферальный объём:</b> {volume} GRAM\n"
            "• <b>Приглашено:</b> {count}</blockquote>{community_status}\n\n"
            "<b>Баланс:</b>\n"
            "<blockquote>• GRAM: {earned_ton}\n"
            "• USDT<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji>: {earned_usdt}</blockquote>\n\n"
            "<b>Ваша реферальная ссылка:</b>\n<code>{link}</code>"
        ),
        TextKey.BACK_BUTTON: "Назад",
        TextKey.MAIN_MENU_BUTTON: "Главное меню",
        TextKey.FAQ_CAPTION: (
            "<tg-emoji emoji-id='5985833664884250583'>❓</tg-emoji> <b>Помощь и часто задаваемые вопросы</b>\n\n"
            "<b>1. Основное</b>\n"
            "<blockquote>GRNT — это гарант-сервис (escrow), обеспечивающий безопасные сделки между пользователями. Средства блокируются до завершения сделки и выпускаются только после подтверждения обеими сторонами.</blockquote>\n\n"
            "<b>2. Как это работает</b>\n"
            "<blockquote>1. Добавьте свой TON-кошелёк в разделе «Мой кошелёк».\n"
            "2. Создайте сделку — опишите условия сделки в чате с гарантом.\n"
            "3. Заблокируйте средства — покупатель переводит оплату, которую удерживает GRNT.\n"
            "4. Подтвердите выполнение — после выполнения условий обе стороны подтверждают.\n"
            "5. Разблокировка — средства автоматически отправляются получателю.</blockquote>\n\n"
            "<b>3. Обязанности сторон</b>\n"
            "<blockquote>• Все условия сделки должны быть согласованы до её начала.\n"
            "• Участники обязаны предоставлять доказательства выполнения условий при возникновении спора.\n"
            "• GRNT не несёт ответственности за мошенничество, внешние переписки и сделки вне сервиса.</blockquote>"
        ),
        TextKey.FAQ_CAPTION_PAGE_2: (
            "<tg-emoji emoji-id='5985833664884250583'>❓</tg-emoji> <b>Помощь и часто задаваемые вопросы</b>\n\n"
            "<b>4. Арбитраж и споры</b>\n"
            "<blockquote>• При разногласиях стороны могут запросить арбитраж GRNT.\n"
            "• Решение арбитра является окончательным и обязательным для сторон.\n"
            "• В случае нарушений аккаунты могут быть ограничены.</blockquote>\n\n"
            "<b>5. Запрещённые сделки</b>\n"
            "<blockquote>Гарант GRNT не поддерживает:\n"
            "• Продажу запрещённых товаров и услуг\n"
            "• Скам, фишинг, обман\n"
            "• Сделки, нарушающие законы или правила Telegram\n"
            "• Переводы и расчёты вне сервиса</blockquote>\n\n"
            "<b>6. Комиссия</b>\n"
            "<blockquote>• Комиссия GRNT составляет 1% и удерживается автоматически при завершении сделки.</blockquote>\n\n"
            "<b>7. Ответственность</b>\n"
            "<blockquote>• GRNT выступает только как нейтральный посредник.\n"
            "• Вся ответственность за достоверность информации и действий лежит на участниках сделки.</blockquote>\n\n"
            "Нужна помощь? Свяжитесь с поддержкой: {support_username}"
        ),
        TextKey.DOCUMENTS_CAPTION: "<tg-emoji emoji-id='6028226658543082010'>📄</tg-emoji> <b>Документы</b>\n\nВыберите документ:",
        TextKey.PRIVACY_BUTTON: "Политика конфиденциальности",
        TextKey.TERMS_BUTTON: "Пользовательское соглашение",
        TextKey.SERVICE_DESCRIPTION_BUTTON: "Описание и условия сервиса",
        TextKey.LANG_RU: "Russian",
        TextKey.LANG_EN: "English",
        TextKey.COMPLETED_DEAL_FEED: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji><b>Сделка</b> <code>#{deal_id}</code>\n\n"
            "<tg-emoji emoji-id='5875206779196935950'>📁</tg-emoji><b>Детали:</b>\n"
            "<blockquote>• Описание: {description}\n"
            "• Продавец получил: {amount} {currency}\n"
            "• Покупатель оплатил: {payment_amount} {currency}</blockquote>\n\n"
            "@grntrobot"
        ),
    },
    Language.EN: {
        TextKey.MAIN_MENU_CAPTION: (
            "<b>Simple deals. We handle the rest.</b>\n\n"
            "<b>Key service features:</b>\n"
            "<blockquote expandable>"
            "<tg-emoji emoji-id='5778139491810155937'>💎</tg-emoji> <b>Starting a deal:</b>\n"
            "Describe the deal terms in the guarantor chat.\n\n"
            "<tg-emoji emoji-id='5931415565955503486'>🤖</tg-emoji> <b>Securing funds:</b>\n"
            "The bot holds the assets until the agreed terms are fulfilled.\n\n"
            "<tg-emoji emoji-id='6028530359975548369'>💎</tg-emoji> <b>Releasing funds:</b>\n"
            "After both parties confirm, the funds are transferred to the recipient.\n\n"
            "<tg-emoji emoji-id='6028226658543082010'>🔨</tg-emoji> <b>Important:</b>\n"
            "<b>GRNT acts as a neutral guarantor and supports only deals that comply with our rules and Telegram policies.</b>\n\n"
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>1%:</b>\n"
            "A fixed 1% fee per completed deal."
            "</blockquote>\n\n"
            "<tg-emoji emoji-id='5967412305338568701'>📅</tg-emoji> <b>Public history:</b> "
            "<a href='https://t.me/grnthub/4'>@grnthub</a>"
        ),
        TextKey.MENU_WALLET: "My wallet",
        TextKey.MENU_CREATE_DEAL: "Create deal",
        TextKey.MENU_MY_DEALS: "My deals",
        TextKey.MENU_SETTINGS: "Settings",
        TextKey.MENU_FAQ: "Help & FAQ",
        TextKey.MENU_DOCUMENTS: "Documents",
        TextKey.MENU_CREATE_DESK: "Create listing",
        TextKey.DESK_KIND_PROMPT: (
            "<tg-emoji emoji-id='5839116473951328489'>📌</tg-emoji> <b>Create a listing</b>\n\n"
            "Choose one of the following:\n<blockquote>WTS — to sell or provide a service.\n\nWTB — to buy or find a service.</blockquote>"
        ),
        TextKey.DESK_DESCRIPTION_PROMPT: (
            "<tg-emoji emoji-id='5839116473951328489'>📌</tg-emoji> <b>Create a listing</b>\n\n"
            "Describe what you offer in the listing.\n\nExample:\n<blockquote>A digital item, gift, account, service, and its terms.</blockquote>"
        ),
        TextKey.DESK_DESCRIPTION_PREVIEW: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\n"
            "<b>Deal details:</b>\n<blockquote>• Description:\n{description}</blockquote>\n\n"
            "Check the description. To change it, simply send replacement text."
        ),
        TextKey.DESK_DEAL_CURRENCY_PROMPT: "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\nChoose the deal currency shown in the listing:",
        TextKey.DESK_AMOUNT_PROMPT: "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\nEnter the deal amount or press Offer if the price is negotiated in DM.\n\nExample: 5 or 12.5",
        TextKey.DESK_PAYMENT_CURRENCY_PROMPT: "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\nChoose the publication payment currency:",
        TextKey.DESK_PAYMENT_INVOICE: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>{kind}</b>\n\n"
            "To publish in Desk, send the exact amount to the guarant wallet.\n\n"
            "<b>Address:</b>\n<code>{wallet}</code>\n\n<b>Amount:</b> {fee} {currency}\n"
            "<b>Required comment:</b> <code>{username}</code>\n\n"
            "<blockquote>The comment may include @ or omit it. The invoice is valid for 15 minutes.</blockquote>"
        ),
        TextKey.DESK_CREATED: (
            "<tg-emoji emoji-id='5875206779196935950'>📅</tg-emoji> <b>Listing</b> <code>#{listing_id}</code> <b>created</b>\n\n"
            "<b>Listing details:</b>\n<blockquote>• Description:\n{description}\n\n• Price: {price}</blockquote>"
        ),
        TextKey.DESK_EXPIRED: "The listing payment window has expired. Create it again.",
        TextKey.DESK_USERNAME_REQUIRED: "Your Telegram profile needs an @username to publish a listing.",
        TextKey.DESK_INVALID_AMOUNT: "Enter a positive number, for example 5 or 12.5.",
        TextKey.OTC_OFFER_PROMPT: (
            "<tg-emoji emoji-id='5775887550262546277'>❗️</tg-emoji> <b>Create an OTC offer</b>\n\n"
            "<b>Details:</b>\n"
            "<blockquote><b>Item:</b> {item}\n<b>Price:</b> {price}</blockquote>\n\n"
            "<b>Enter your offer amount in GRAM:</b>"
        ),
        TextKey.OTC_OFFER_SENT: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji>"
            "Your offer of <b>{amount} GRAM</b> has been sent to the owner. "
            "Wait for their decision."
        ),
        TextKey.OTC_OFFER_INCOMING: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>New OTC-offer</b>\n\n"
            "<b>Details:</b>\n"
            "<blockquote><b>Item:</b> {item}\n"
            "<b>Amount:</b> {amount} GRAM\n"
            "<b>Buyer:</b> {buyer}</blockquote>\n\n"
            "The bot only connects the parties.\n"
            "Payment is settled directly between the users.\n\n"
            "<b>Accept or decline the offer:</b>"
        ),
        TextKey.OTC_OFFER_RESULT: (
            "<tg-emoji emoji-id='5879785854284599288'>ℹ️</tg-emoji> <b>OTC-offer status</b>\n\n"
            "<b>Details:</b>\n"
            "<blockquote><b>Item:</b> {item}\n"
            "<b>Offer amount:</b> {amount} GRAM</blockquote>\n\n"
            "<b>Status:</b> {status}\n\n"
            "Contact the other party to proceed with the deal.\n"
            "Payment is settled directly between the users.\n\n"
            "The bot does not transfer GRAM, NFTs, or other assets — it only connects the parties."
        ),
        TextKey.OTC_OFFER_UNAVAILABLE: (
            "The listing does not exist, is no longer active, or belongs to you."
        ),
        TextKey.OTC_OFFER_INVALID_AMOUNT: (
            "Enter a positive amount with no more than 9 decimal places."
        ),
        TextKey.OTC_OFFER_COOLDOWN: (
            "You can send another offer in {seconds} sec."
        ),
        TextKey.OTC_OFFER_ALREADY_RESOLVED: (
            "This offer has already been processed or is unavailable."
        ),
        TextKey.OTC_OFFER_ACCEPT_BUTTON: "Accept",
        TextKey.OTC_OFFER_DECLINE_BUTTON: "Decline",
        TextKey.OTC_OFFER_PROFILE_BUTTON: "Profile",
        TextKey.WALLET_PROMPT: "<tg-emoji emoji-id='5769403330761593044'>👛</tg-emoji> <b>My wallet</b>\n\nSend the TON address you want to link to your profile.",
        TextKey.WALLET_ACTIVE_PROMPT: (
            "<tg-emoji emoji-id='5769403330761593044'>👛</tg-emoji> <b>My wallet</b>\n\n<b>Current address:</b>\n"
            "<blockquote><a href=\"{wallet_url}\">{wallet_short}</a></blockquote>\n\n"
            "Want to change it? Send a new address."
        ),
        TextKey.WALLET_SAVED: "Wallet saved:\n<blockquote><code>{wallet}</code></blockquote>",
        TextKey.WALLET_INVALID: "This does not look like a TON address. Please try again.",
        TextKey.DEAL_CREATE_INTRO: "<tg-emoji emoji-id='5956561916573782596'>💬</tg-emoji> <b>Create a deal</b>\n\nChoose the deal type:",
        TextKey.DEAL_TYPE_OFFER: "Offer",
        TextKey.DEAL_TYPE_CHANNEL: "Channel",
        TextKey.DEAL_CHANNEL_WARNING: (
            "<tg-emoji emoji-id='5839116473951328489'>⭐️</tg-emoji> <b>Channel deal</b>\n\n"
            "<blockquote>Add the bot as a channel administrator and grant it full rights, including inviting users and appointing administrators. Then send the channel @username or ID, or forward a message from the channel.</blockquote>\n\n"
            "<blockquote>The buyer will join through an invite link. After payment, the seller manually transfers ownership. The bot verifies the status automatically and starts the payout only after verification.</blockquote>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> <b>Do not remove the bot from the administrators until the deal is complete!</b>"
        ),
        TextKey.DEAL_CHANNEL_INVALID: (
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> <b>Channel validation failed</b>\n\n"
            "<blockquote>{reason}</blockquote>\n\n"
            "Fix the permissions and send the channel again."
        ),
        TextKey.DEAL_CHANNEL_VERIFIED: "Channel “{title}” verified.",
        TextKey.DEAL_CHANNEL_INVITE_UNAVAILABLE: (
            "A secure channel invite link could not be created, so payment is unavailable. "
            "The seller must verify that the bot is still an administrator with permission to invite users."
        ),
        TextKey.DEAL_PAY_BUTTON: "Pay in Tonkeeper",
        TextKey.DEAL_CHANNEL_JOIN_BUTTON: "Request channel access",
        TextKey.DEAL_DESCRIPTION_PROMPT: (
            "<tg-emoji emoji-id='5985630530111020079'>💬</tg-emoji> <b>Create an offer</b>\n\nDescribe what you offer in the deal.\n\n"
            "Example:\n"
            "<blockquote>A digital item, gift, account, service, and its delivery terms.</blockquote>"
        ),
        TextKey.DEAL_CURRENCY_PROMPT: "<tg-emoji emoji-id='5956561916573782596'>💬</tg-emoji> <b>Create a deal</b>\n\nChoose the deal currency:",
        TextKey.DEAL_AMOUNT_PROMPT: "<tg-emoji emoji-id='5956561916573782596'>💬</tg-emoji> <b>Create a deal</b>\n\nEnter the deal amount.\n\nExample: 5 or 12.5",
        TextKey.DEAL_AMOUNT_INVALID: "Please enter a positive number.",
        TextKey.DEAL_AMOUNT_TOO_SMALL: (
            "<blockquote><tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Minimum deal amount — {minimum} {currency} <tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji></blockquote>\n\n"
            "The service fee is added to the invoice; network gas is paid separately."
        ),
        TextKey.DEAL_CREATED: (
            "<tg-emoji emoji-id='5879895758202735862'>🔒</tg-emoji> <b>Deal</b> <code>#{deal_id}</code> <b>created</b>\n\n"
            "Deal details:\n"
            "<blockquote>• Description: {description}\n"
            "• Seller will receive: {amount} {currency}\n"
            "• Buyer will pay: {payment_amount} {currency}</blockquote>\n\n"
            "Send this link to the buyer so they can join:\n{deep_link}"
        ),
        TextKey.DEAL_CANCEL_BUTTON: "Cancel deal",
        TextKey.DEAL_CONFIRM_BUTTON: "Complete deal",
        TextKey.DEAL_DELIVER_BUTTON: "Service delivered",
        TextKey.DEAL_DISPUTE_BUTTON: "Open dispute",
        TextKey.DEAL_JOINED: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> <b>Deal</b> <code>#{deal_id}</code>\n"
            "<tg-emoji emoji-id='5942877472163892475'>👤</tg-emoji> You are the buyer.\n\n"
            "Seller's completed deals: {seller_deals}\n\n"
            "<b>Deal details:</b>\n"
            "<blockquote><b>• Deal code:</b> <code>#{deal_id}</code>\n"
            "• Description: {description}</blockquote>\n\n"
            "• Payment address: {wallet_address}\n\n"
            "• Amount due: {amount} {currency}\n\n"
            "• Comment (optional): {deal_id}\n\n"
            "<blockquote><tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Send the exact amount to the specified address. The comment may be omitted.</blockquote>\n\n"
            "After payment, the bot will verify the transfer automatically."
        ),
        TextKey.DEAL_NOT_FOUND: "Deal not found.",
        TextKey.DEAL_FORBIDDEN: "You do not have access to this deal.",
        TextKey.DEAL_ALREADY_CANCELLED: "This deal can no longer be cancelled.",
        TextKey.DEAL_CANCELLED: "Deal cancelled.",
        TextKey.DEAL_LIST_EMPTY: "<tg-emoji emoji-id='5967548335542767952'>📋</tg-emoji> <b>My deals</b>\n\nNothing here yet",
        TextKey.DEAL_LIST_CAPTION: "<tg-emoji emoji-id='5967548335542767952'>📋</tg-emoji> <b>My deals:</b>",
        TextKey.DEAL_CARD: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji> "
            "<b>Deal</b> <code>#{deal_id}</code>\n\n"
            "<b>Details:</b>\n"
            "<blockquote>• Description: {description}\n"
            "• Seller {seller_amount_verb}: {amount} {currency}\n"
            "• Buyer {buyer_amount_verb}: {payment_amount} {currency}</blockquote>\n\n"
            "<b>Seller:</b>\n{seller}\n\n"
            "<b>Buyer:</b>\n{buyer}{channel_details}\n\n"
            "<b>Status:</b> {status}"
        ),
        TextKey.DEAL_PAID_BUYER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Payment found and confirmed!</b>\n"
            "Your payment for deal <code>#{deal_id}</code> was processed successfully.\n\n"
            "Transaction:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">View in TON Viewer</a>\n\n"
            "Deal details:\n"
            "<blockquote>• Description: {description}\n"
            "• Seller: {seller}</blockquote>\n\n"
            "Wait for the seller to confirm that the service has been delivered."
        ),
        TextKey.DEAL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Payment confirmed!</b>\n"
            "The buyer paid for deal <code>#{deal_id}</code>.\n\n"
            "Transaction:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">View in TON Viewer</a>\n\n"
            "Deal details:\n"
            "<blockquote>• Description: {description}\n"
            "• Buyer: {buyer}</blockquote>\n\n"
            "<tg-emoji emoji-id='5985780596268339498'>🤖</tg-emoji> The funds have been credited to the bot wallet.\n"
            "You may now deliver the service. Remember to press the button below!"
        ),
        TextKey.DEAL_CHANNEL_PAID_BUYER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Payment found and confirmed!</b>\n"
            "Your payment for deal <code>#{deal_id}</code> was processed successfully.\n\n"
            "Transaction:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">View in TON Viewer</a>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Join the channel using the deal button and wait for the seller to transfer ownership manually. The bot will verify it automatically."
        ),
        TextKey.DEAL_CHANNEL_PAID_SELLER: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Payment confirmed!</b>\n"
            "The buyer paid for deal <code>#{deal_id}</code>.\n\n"
            "Transaction:\n"
            "<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> <a href=\"{transaction_url}\">View in TON Viewer</a>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Transfer ownership manually in Telegram settings and do not remove the bot from the administrators. Once the buyer has creator status, the bot will start the payout automatically."
        ),
        TextKey.DEAL_RELEASE_ACCEPTED: (
            "<b>Deal completion and payout:</b>\n"
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Deal completed successfully!\n\n"
            "Deal details:\n"
            "<blockquote>• Description: {description}\n"
            "• Seller received: {seller_amount} {currency}\n"
            "• Buyer paid: {payment_amount} {currency}</blockquote>\n\n"
            "<tg-emoji emoji-id='5843908536467198016'>🔄</tg-emoji> The seller payout is being processed.\n"
            "They will receive a notification after the transaction is complete."
        ),
        TextKey.DEAL_CONFIRMED: "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Completed",
        TextKey.DEAL_WAIT_WALLET: "The seller has not linked a payout wallet yet.",
        TextKey.DEAL_BUYER_WALLET_REQUIRED: (
            "Link a TON wallet before joining. It will be used as the safe refund destination."
        ),
        TextKey.DEAL_PAYOUT_BLOCKED: (
            "The payout was stopped before broadcast because the guarantor wallet lacks gas. "
            "Funds remain with the guarantor; contact support."
        ),
        TextKey.DEAL_DELIVERED: (
            "<b>Fulfilment and delivery:</b>\n"
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> Service marked as delivered!\n\n"
            "The buyer has been notified and can confirm receipt."
        ),
        TextKey.DEAL_DELIVERY_NOTICE: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> The seller delivered the service!\n\n"
            "The seller confirmed that the service was delivered:\n"
            "<blockquote>• Deal code: <code>#{deal_id}</code>\n"
            "• Description: {description}\n"
            "• Amount paid: {payment_amount} {currency}</blockquote>\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>⚠️</tg-emoji> Please check the quality of the completed work.\n\n"
            "<tg-emoji emoji-id='5881702736843511327'>ℹ️</tg-emoji> After your confirmation, the funds will be transferred to the seller.\n"
            "If you do not confirm receipt or open a dispute within 1 hour, the deal will be completed automatically."
        ),
        TextKey.DEAL_DISPUTE_PROMPT: (
            "Describe the problem in one message (10–1000 characters). Screenshots are not stored by "
            "the bot; send them directly to support if needed."
        ),
        TextKey.DEAL_DISPUTE_INVALID: "Description must contain 10 to 1000 characters.",
        TextKey.DEAL_DISPUTE_CREATED: (
            "Dispute ticket created. Funds are frozen with the guarantor. "
            "Contact support and include the deal ID."
        ),
        TextKey.DEAL_REFUNDED: "The TON network confirmed the buyer refund.",
        TextKey.DEAL_CANCELLED_BY_SELLER: "The seller cancelled the deal\nDeal code: <code>#{deal_id}</code>",
        TextKey.DEAL_PAYOUT_RECEIVED: (
            "<tg-emoji emoji-id='5776375003280838798'>✅</tg-emoji> <b>Deal completed successfully!</b>\n"
            "<tg-emoji emoji-id='5778318458802409852'>💰</tg-emoji> <b>Payout received!</b>\n\n"
            "Deal details:\n"
            "<blockquote>• Description: {description}\n"
            "• Amount: {amount} {currency}\n"
            "• Wallet: {wallet}</blockquote>\n\n"
            "Transaction:\n"
            "<a href=\"{transaction_url}\"><tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji> View in TON Viewer</a>\n\n"
            "Thank you for using our service! <tg-emoji emoji-id='5908808657700655253'>🐱</tg-emoji>"
        ),
        TextKey.SETTINGS_CAPTION: "<tg-emoji emoji-id='5877260593903177342'>⚙️</tg-emoji> <b>Settings</b>",
        TextKey.SETTINGS_REFERRALS: "Referrals",
        TextKey.SETTINGS_LANGUAGE: "Language",
        TextKey.SETTINGS_SUPPORT: "Support",
        TextKey.LANGUAGE_PROMPT: (
            "<tg-emoji emoji-id='5449408995691341691'>🇷🇺</tg-emoji> ← Выберите язык бота прежде чем начать пользоваться.\n\n"
            "<tg-emoji emoji-id='5202021044105257611'>🇺🇸</tg-emoji> ← Choose the bot's language before you start using it."
        ),
        TextKey.LANGUAGE_SAVED: "<tg-emoji emoji-id='5776375003280838798'>🎉</tg-emoji> <b>Language successfully set!</b>",
        TextKey.SUPPORT_TEXT: "<tg-emoji emoji-id='5967411695453213733'>🛟</tg-emoji> <b>Support</b>\n\nFor support or disputes, contact {support_username}.",
        TextKey.REFERRAL_CAPTION: (
            "<tg-emoji emoji-id='5942877472163892475'>👥</tg-emoji> <b>Referrals</b>\n\n"
            "<b>Details:</b>\n"
            "<blockquote>• <b>Level:</b> {level}\n"
            "• <b>Referral percentage:</b> {rate}%\n"
            "• <b>Referral volume:</b> {volume} GRAM\n"
            "• <b>Invited:</b> {count}</blockquote>{community_status}\n\n"
            "<b>Balance:</b>\n"
            "<blockquote>• GRAM: {earned_ton}\n"
            "• USDT<tg-emoji emoji-id='5778546023349621090'>💎</tg-emoji>: {earned_usdt}</blockquote>\n\n"
            "<b>Your referral link:</b>\n"
            "<code>{link}</code>"
        ),
        TextKey.BACK_BUTTON: "Back",
        TextKey.MAIN_MENU_BUTTON: "Main menu",
        TextKey.FAQ_CAPTION: (
            "<tg-emoji emoji-id='5985833664884250583'>❓</tg-emoji> <b>Help & FAQ</b>\n\n"
            "<b>1. Overview</b>\n"
            "<blockquote>GRNT is an escrow service that enables secure deals between users. Funds are held until the deal is completed and released only after confirmation by both parties.</blockquote>\n\n"
            "<b>2. How it works</b>\n"
            "<blockquote>1. Add your TON wallet in the “My wallet” section.\n"
            "2. Create a deal — describe its terms in the guarantor chat.\n"
            "3. Secure the funds — the buyer sends payment, which GRNT holds.\n"
            "4. Confirm completion — after the terms are fulfilled, both parties confirm.\n"
            "5. Release — the funds are automatically sent to the recipient.</blockquote>\n\n"
            "<b>3. Responsibilities of the parties</b>\n"
            "<blockquote>• All deal terms must be agreed before the deal begins.\n"
            "• Participants must provide evidence that the terms were fulfilled if a dispute arises.\n"
            "• GRNT is not responsible for fraud, external correspondence, or deals made outside the service.</blockquote>"
        ),
        TextKey.FAQ_CAPTION_PAGE_2: (
            "<tg-emoji emoji-id='5985833664884250583'>❓</tg-emoji> <b>Help & FAQ</b>\n\n"
            "<b>4. Arbitration and disputes</b>\n"
            "<blockquote>• If the parties disagree, they may request GRNT arbitration.\n"
            "• The arbitrator’s decision is final and binding on both parties.\n"
            "• Accounts may be restricted in case of violations.</blockquote>\n\n"
            "<b>5. Prohibited deals</b>\n"
            "<blockquote>GRNT does not support:\n"
            "• The sale of prohibited goods or services\n"
            "• Scams, phishing, or deception\n"
            "• Deals that violate laws or Telegram rules\n"
            "• Transfers and settlements outside the service</blockquote>\n\n"
            "<b>6. Fee</b>\n"
            "<blockquote>• GRNT charges a 1% fee automatically when a deal is completed.</blockquote>\n\n"
            "<b>7. Liability</b>\n"
            "<blockquote>• GRNT acts solely as a neutral intermediary.\n"
            "• Deal participants are fully responsible for the accuracy of their information and actions.</blockquote>\n\n"
            "Need help? Contact support: {support_username}"
        ),
        TextKey.DOCUMENTS_CAPTION: "<tg-emoji emoji-id='6028226658543082010'>📄</tg-emoji> <b>Documents</b>\n\nChoose a document:",
        TextKey.PRIVACY_BUTTON: "Privacy policy",
        TextKey.TERMS_BUTTON: "Terms of service",
        TextKey.SERVICE_DESCRIPTION_BUTTON: "Service description and conditions",
        TextKey.LANG_RU: "Russian",
        TextKey.LANG_EN: "English",
        TextKey.COMPLETED_DEAL_FEED: (
            "<tg-emoji emoji-id='6028226658543082010'>📋</tg-emoji><b>Deal</b> <code>#{deal_id}</code>\n\n"
            "<tg-emoji emoji-id='5875206779196935950'>📁</tg-emoji><b>Details:</b>\n"
            "<blockquote>• Description: {description}\n"
            "• Seller received: {amount} {currency}\n"
            "• Buyer paid: {payment_amount} {currency}</blockquote>\n\n"
            "@grntrobot"
        ),
    },
}
