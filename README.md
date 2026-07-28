# Gift Guarant

Telegram escrow-бот на Python 3.14.3, aiogram 3.x, FastAPI, Supabase и TON. Поддерживает офферы, продажу Telegram-каналов, GRAM/TON и USDT в сети TON, возвраты, споры, реферальный баланс и административное управление.

## Архитектура

- `app/handlers` — Telegram Update, FSM и навигация без запросов к БД/TON.
- `app/services` — сценарии сделок, выплат, возвратов, каналов и рефералов.
- `app/repositories` — единственная точка доступа к Supabase RPC/REST.
- `app/ton` — формирование кошельков, платежей и проверка TonAPI.
- `app/tasks` — независимые циклы оплаты, collection, payout/refund и retention.
- `app/api` — FastAPI, health checks, webhook, документы и Render keep-alive.
- `app/database` — полная схема, функции, права и последовательные миграции.

Продавец создаёт сделку и передаёт ссылку покупателю. Покупатель привязывает кошелёк, вступает и оплачивает `D + 1% + gas`. После подтверждения услуги продавец получает `D`; сервисная комиссия отправляется отдельно. При отмене после оплаты запускается возврат по существующей refund-логике. Платёжного таймера нет.

## Запуск

1. Установите Python 3.14.3.
2. Скопируйте `.env.example` в `.env` и заполните секреты.
3. Создайте окружение и установите зависимости:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.main
```

Проверки: `GET /healthz`, `GET /readyz`, `GET /ping`.

## Supabase

Для новой базы выполните в SQL Editor по порядку:

1. `app/database/schema.sql`
2. `app/database/routines.sql`
3. `app/database/lifecycle.sql`
4. `app/database/permissions.sql`

Для уже работающей базы дополнительно примените миграции в порядке имени. Для этого обновления обязательны:

1. `app/database/migrations/20260728_navigation_notifications.sql`
2. `app/database/migrations/20260728_cancellation_flow.sql`

`SUPABASE_KEY` должен быть серверным `service_role`/secret key. Его нельзя публиковать в GitHub или передавать клиенту.

## TON

- `TON_MNEMONIC` — ровно 24 слова кошелька гаранта.
- `TON_GUARANT_ADDRESS` обязан соответствовать этой mnemonic и выбранной сети.
- Для USDT используется официальный master-адрес из `USDT_MASTER_ADDRESS`.
- На кошельке гаранта должен быть TON для gas, включая USDT jetton transfer.
- Проверка оплаты использует адрес, актив, сумму и memo; один комментарий не считается достаточным доказательством.

## Render Deploy

Проект содержит `Dockerfile` и `render.yaml`. Создайте Web Service из репозитория, добавьте секретные переменные из `.env.example` и используйте `/healthz` как Health Check Path. `APP_BASE_URL` и `RENDER_EXTERNAL_URL` должны быть обычными URL без Markdown-скобок.

Keep-alive вызывает `/ping` раз в 840 секунд. Непрерывность бесплатного инстанса всё равно зависит от правил и лимитов Render.

## Медиа интерфейса

Заменяемые файлы хранятся в `app/assets/media`. Поддерживаются `.gif`, `.mp4`, `.png`, `.jpg`, `.jpeg`. Имена экранов:

- `main_menu.gif`
- `wallet.gif`
- `deals.gif`
- `deal.gif`
- `faq.gif`
- `documents.gif`
- `settings.gif`
- `language.gif`
- `referrals.gif`
- `deal_create.gif`
- `deal_join.gif`

После замены файла перезапустите сервис. Если файл отсутствует, используется `app/assets/menu.png`.

## Environment Variables

Полный безопасный шаблон находится в `.env.example`. Фиксированные бизнес-параметры по умолчанию: комиссия сервиса `1%`, минимум GRAM/TON `1`, минимум USDT `1`, максимум пять сделок на странице, хранение неуспешных сделок до 30 дней.

Никогда не коммитьте `.env`, Telegram token, Supabase secret, TonAPI key или mnemonic. Если секрет уже публиковался, его необходимо отозвать и выпустить заново.
