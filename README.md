# Gift Guarant

Production-ready Telegram-бот для сделок с гарантом в сети TON. Бот принимает
оплату покупателя на отдельный адрес сделки, проверяет транзакцию и переводит
сумму продавцу. HTTP-часть работает на FastAPI, Telegram — на Aiogram 3.x,
данные и атомарные операции хранятся в Supabase/PostgreSQL.

## Стек

- CPython 3.14.3;
- Aiogram 3.30.0;
- FastAPI 0.139.2 и Uvicorn 0.51.0;
- Supabase Python 2.31.0 и PostgreSQL;
- Pydantic 2.13.4 и pydantic-settings 2.14.2;
- tonutils 2.1.0 и TonAPI.

Версии зафиксированы в `requirements.txt`, Docker-образ — в `Dockerfile`.

## Архитектура

```text
app/
|-- main.py          # точка входа процесса и Uvicorn
|-- loader.py        # composition root: создание и внедрение зависимостей
|-- bot.py           # фабрика Aiogram Dispatcher
|-- config.py        # типизированные настройки окружения
|-- api/             # FastAPI lifecycle, health-check и Telegram webhook
|-- core/            # Enum, константы, исключения, Protocol, логирование
|-- database/        # адаптер Supabase и PostgreSQL schema/RPC
|-- handlers/        # тонкие Telegram-контроллеры
|-- keyboards/       # клавиатуры и типизированный CallbackData
|-- locales/         # сообщения и локализация
|-- middleware/      # Telegram-контекст текущего пользователя
|-- models/          # доменные сущности и DTO
|-- repositories/    # все операции чтения и записи Supabase
|-- services/        # бизнес-сценарии без Telegram, SQL и TON SDK
|-- states/          # Aiogram FSM
|-- tasks/           # монитор оплаты, выплат и очистка данных
`-- ton/             # TON-клиент, суммы, парсинг и transport DTO
```

Направление зависимостей:

```text
handlers / middleware / API / background tasks
                         |
                         v
                      services
                         |
                         v
                 core Protocol contracts
                         ^
                         |
       repositories / TON adapter / Telegram notifier
```

- Handler валидирует Update, вызывает service и формирует Telegram-ответ.
- Service содержит бизнес-логику и зависит от Protocol-интерфейсов.
- Только repository обращается к Supabase. Синхронный SDK изолирован через
  `asyncio.to_thread` внутри `SupabaseDatabase.run()`.
- Только `app/ton` знает о tonutils и TonAPI.
- Зависимости создаются один раз в `app/loader.py` и внедряются через
  конструкторы.
- Callback payload создаётся через Aiogram `CallbackData`, без ручного разбора
  строк.

## Как проходит сделка

1. Продавец создаёт сделку, указывает описание, сумму и кошелёк выплаты.
2. Бот резервирует уникальный `subwallet_id` и вычисляет отдельный адрес
   WalletV4R2 для сделки.
3. Покупатель присоединяется и отправляет точную сумму с комиссией и memo сделки.
4. Фоновый монитор сверяет адрес получателя, сумму в nanoTON, memo, состояние
   транзакции и отсутствие bounce.
5. PostgreSQL RPC атомарно фиксирует платёж и разрешает только одну выплату.
6. Подписанный BOC и hash внешнего сообщения сохраняются до отправки.
7. TonAPI trace подтверждает успешное выполнение либо фиксирует bounce/error.

`deals.amount` — чистая сумма продавцу. При комиссии `0.03` сделка на 870 TON
требует от покупателя 896.1 TON, после чего продавцу отправляется 870 TON.

USDT в TON намеренно отключён в интерфейсе и service. Jetton-переводы нельзя
обрабатывать как native TON: для них нужна отдельная проверка jetton wallet,
master contract, opcode, decimals и payout-механика.

## Быстрый запуск

### 1. Подготовить окружение

Linux/macOS:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Заполните `.env`, затем примените `app/database/schema.sql` в Supabase.

### 2. Запустить приложение

```bash
python -m app.main
```

По умолчанию бот использует long polling, а FastAPI слушает
`http://0.0.0.0:8000`.

### 3. Проверить состояние

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

- `/healthz` проверяет, что HTTP-процесс работает;
- `/readyz` показывает состояние TON-клиента и фонового монитора.

### Запуск через Docker

```bash
docker build -t gift-guarant .
docker run --rm --env-file .env -p 8000:8000 gift-guarant
```

Контейнер использует `python:3.14.3-slim` и запускается от непривилегированного
пользователя.

## Переменные окружения

Скопируйте `.env.example` в `.env`. Файл `.env` запрещён к коммиту через
`.gitignore`.

### Обязательные секреты

| Переменная | Назначение |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather. |
| `SUPABASE_URL` | URL проекта вида `https://PROJECT.supabase.co`. |
| `SUPABASE_KEY` | Серверный Supabase secret key либо legacy `service_role`; не anon/publishable key. |
| `TON_MNEMONIC` | 24 слова выделенного кошелька гаранта. Управляет реальными средствами. |

### Приложение и Telegram

| Переменная | По умолчанию | Описание |
|---|---:|---|
| `APP_NAME` | `Gift Guarant` | Имя FastAPI-приложения. |
| `APP_HOST` | `0.0.0.0` | Интерфейс HTTP-сервера. На Render не менять. |
| `APP_PORT` | `8000` | Порт Uvicorn; на Render задать `10000`. |
| `APP_BASE_URL` | пусто | Публичный HTTPS URL, обязателен в webhook-режиме. |
| `TELEGRAM_BOT_USERNAME` | пусто | Username бота без `@`. |
| `TELEGRAM_USE_POLLING` | `true` | `true` — polling, `false` — webhook. |
| `TELEGRAM_WEBHOOK_PATH` | `/telegram/webhook` | Путь входящих Telegram Update. |
| `TELEGRAM_WEBHOOK_SECRET` | пусто | Случайный секрет webhook; обязателен при `false`. |
| `SUPPORT_USERNAME` | `@msk_deputat` | Контакт поддержки. |

### Supabase

| Переменная | По умолчанию | Описание |
|---|---:|---|
| `SUPABASE_URL` | — | URL PostgreSQL API проекта. |
| `SUPABASE_KEY` | — | Только серверный ключ с ролью `service_role`. |

### TON и TonAPI

| Переменная | По умолчанию | Описание |
|---|---:|---|
| `TON_API_ENDPOINT` | `https://tonapi.io/v2` | REST endpoint TonAPI. Для testnet используйте testnet endpoint `/v2`. |
| `TON_API_KEY` | пусто | API key TonAPI; для production рекомендуется задать. |
| `TON_MNEMONIC` | — | 24 слова кошелька гаранта через пробел. |
| `TON_NETWORK` | `mainnet` | `mainnet` или `testnet`; сеть должна совпадать с endpoint. |
| `TON_WORKCHAIN` | `0` | Workchain создаваемых адресов. |
| `TON_REQUEST_TIMEOUT_MS` | `15000` | Timeout HTTP-запросов к TON API. |
| `TON_TRANSFER_TTL_SECONDS` | `60` | Срок действия подписанного сообщения выплаты. |
| `TON_TRACE_GRACE_SECONDS` | `120` | Время ожидания появления trace после отправки. |
| `TON_TRANSACTION_SCAN_LIMIT` | `50` | Число последних транзакций для проверки оплаты. |

### Сделки и фоновые задачи

| Переменная | По умолчанию | Описание |
|---|---:|---|
| `DEAL_POLL_INTERVAL_SECONDS` | `15` | Интервал проверки платежей и выплат. |
| `DEAL_PAYMENT_TIMEOUT_SECONDS` | `900` | Время на оплату присоединённой сделки. |
| `FAILED_DEAL_RETENTION_DAYS` | `30` | Хранение неуспешных сделок, допустимо 1–30 дней. |
| `RETENTION_CLEANUP_INTERVAL_SECONDS` | `86400` | Интервал запуска очистки. |
| `ESCROW_FEE_RATE` | `0.03` | Комиссия гаранта: `0.03` = 3%. |
| `REFERRAL_FEE_SHARE` | `0.01` | Реферальная доля: `0.01` = 1%. |
| `AUTO_PAYOUT_AFTER_PAYMENT` | `true` | Автоматически начать выплату после подтверждения оплаты. |
| `DEALS_PAGE_SIZE` | `8` | Количество сделок на странице. |
| `DEFAULT_LANGUAGE` | `ru` | Язык нового пользователя: `ru` или `en`. |
| `DEFAULT_CURRENCY` | `TON` | Рабочая валюта; сейчас поддерживается только `TON`. |

## Supabase

### Первичная настройка

1. Создайте проект Supabase и откройте `SQL Editor`.
2. Выполните весь файл `app/database/schema.sql` одним запуском.
3. В `Project Settings -> API Keys` получите server-side secret key. Если проект
   использует старые ключи, допустим legacy `service_role`.
4. Запишите URL и ключ в `SUPABASE_URL` и `SUPABASE_KEY`.
5. Запустите приложение и проверьте `/readyz` и логи старта.

Схема создаёт:

- `users` — Telegram-пользователи и кошельки;
- `deals` — состояние сделки и подтверждённый платёж;
- `deal_payments` — уникальные on-chain платежи;
- `payout_attempts` — идемпотентные попытки выплат, BOC и trace status;
- `referrals` — связи и начисления;
- RPC-функции для атомарного присоединения покупателя, фиксации платежа,
  выплаты, рефералов и retention cleanup.

RLS включён для всех таблиц, а выполнение чувствительных RPC выдано только
`service_role`. Поэтому серверный ключ должен находиться только в backend
environment. Не отправляйте его в Telegram, браузер, клиентское приложение или
Git. Для последующих изменений production-схемы храните версионные migrations и
применяйте их через Supabase CLI, а не редактируйте таблицы вручную.

Неуспешные сделки со статусами `cancelled`, `creation_failed`, `payout_failed`
и `payout_bounced` удаляются фоновой задачей не позднее заданного срока, максимум
30 дней. Связанные payment/payout строки удаляются каскадно. Успешные сделки и
пользователи сохраняются.

## TON

Бот использует одну мнемонику и уникальный `subwallet_id` для каждой сделки.
Разные subwallet ID дают независимые WalletV4R2-адреса с отдельными балансами и
`seqno`, хотя ключевая пара общая. Поэтому таблица `deals` хранит `subwallet_id`
как уникальное 32-битное значение.

Правила безопасной настройки:

1. Создайте отдельную мнемонику только для этого сервиса. Не используйте личный
   кошелёк владельца.
2. Сначала задайте `TON_NETWORK=testnet` и testnet TonAPI endpoint, проведите
   полный цикл оплаты и выплаты тестовыми средствами.
3. Перед mainnet ещё раз проверьте сеть, endpoint, адрес продавца, fee и лимиты.
4. Храните `TON_MNEMONIC` только в secret environment Render; смена мнемоники
   меняет все вычисляемые адреса сделок.
5. Не удаляйте записи `payout_attempts`: сохранённый BOC/hash нужен для
   безопасного восстановления после перезапуска между подписью и broadcast.
6. Оставляйте на адресе сделки запас на blockchain fee. Сумма покупателя
   включает комиссию сервиса, а продавцу перечисляется только `deals.amount`.

Платёж засчитывается только при одновременном совпадении destination, точной
суммы в nanoTON, memo/public ID и успешного неброшенного сообщения. Выплата
считается завершённой только после успешного TonAPI trace, а не сразу после
broadcast.

## Render Deploy

Проект разворачивается как Docker Web Service — Dockerfile уже закрепляет
CPython 3.14.3.

1. Загрузите проект в приватный Git-репозиторий без `.env`.
2. В Render выберите `New -> Web Service` и подключите репозиторий.
3. Укажите `Language: Docker`, нужную branch и корень, где лежит `Dockerfile`.
4. Выберите **один** экземпляр сервиса. Несколько экземпляров одновременно
   запустят несколько polling/retention циклов.
5. В `Environment` добавьте переменные из `.env.example` и секреты.
6. Обязательно задайте `APP_HOST=0.0.0.0` и `APP_PORT=10000`.
7. В `Health Check Path` укажите `/healthz`.
8. Выполните deploy и проверьте `https://SERVICE.onrender.com/healthz` и
   `/readyz`.

### Polling на Render

Для простого запуска:

```dotenv
TELEGRAM_USE_POLLING=true
APP_HOST=0.0.0.0
APP_PORT=10000
```

Webhook Telegram при этом не устанавливается. Нельзя запускать тот же токен
бота ещё в одном polling-процессе.

### Webhook на Render

```dotenv
TELEGRAM_USE_POLLING=false
APP_BASE_URL=https://SERVICE.onrender.com
TELEGRAM_WEBHOOK_PATH=/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=long-random-secret
APP_HOST=0.0.0.0
APP_PORT=10000
```

URL должен быть HTTPS и не оканчиваться `/`. При старте lifecycle регистрирует
webhook, а endpoint проверяет заголовок Telegram secret token.

### Важное ограничение Free instance

Бесплатный Render Web Service останавливается после 15 минут без входящего HTTP
трафика. В спящем процессе не работают Telegram polling и монитор TON-платежей.
Внешний ping раз в 15 минут находится на границе тайм-аута и не гарантирует
непрерывную работу; если это временное решение, используйте интервал меньше
15 минут, например 10–14 минут, и ping `/healthz`.

Для production с деньгами используйте постоянно работающий paid instance.
Файловая система Render эфемерна, но бот не хранит бизнес-данные локально —
источником истины остаётся Supabase. Всё равно не сохраняйте важные данные в
файлы контейнера.

## Диагностика

| Симптом | Что проверить |
|---|---|
| `/readyz` показывает `starting` | Доступность TonAPI, `TON_API_KEY`, сеть и логи monitor task. |
| Telegram отвечает конфликтом polling | Не запущен ли второй процесс с тем же bot token. |
| Webhook возвращает 403 | Совпадает ли `TELEGRAM_WEBHOOK_SECRET` в Render и Telegram webhook. |
| Supabase возвращает RLS/permission error | Используется ли server secret/service-role key, применены ли все GRANT из schema.sql. |
| Оплата не найдена | Точный адрес сделки, сумма, memo, сеть и глубина `TON_TRANSACTION_SCAN_LIMIT`. |
| Выплата зависла в submitted | TonAPI trace, баланс subwallet и корректность адреса продавца. |

## Проверка перед production

- `.env` и мнемоника отсутствуют в Git history;
- Supabase server key и TON mnemonic добавлены как Render secrets;
- тестовый полный цикл успешно пройден в testnet;
- используется один экземпляр фонового обработчика;
- `/healthz` доступен, `/readyz` показывает `ok`;
- выбран постоянно работающий Render instance;
- настроены резервные копии Supabase и мониторинг ошибок;
- mainnet fee и минимальный остаток на оплату gas проверены малой суммой.
