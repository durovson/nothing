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
|-- api/             # FastAPI lifecycle, ping/health-check и Telegram webhook
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
2. Бот атомарно резервирует идентификатор кошелька и вычисляет отдельный
   WalletV5R1-адрес для новой сделки. Сделки, созданные до миграции, продолжают
   использовать свои WalletV4R2-адреса.
3. Покупатель присоединяется и отправляет точную сумму с комиссией и memo сделки.
4. Фоновый монитор сверяет сумму фактического credit phase в nanoTON, memo,
   отсутствие bounce и сохранение средств на адресе сделки.
5. PostgreSQL RPC атомарно фиксирует платёж; средства остаются на отдельном
   escrow-subwallet сделки.
6. Только покупатель может подтвердить получение товара или услуги и запустить
   единственную выплату.
7. Подписанный BOC и hash внешнего сообщения сохраняются до отправки.
8. TonAPI trace подтверждает успешное выполнение либо фиксирует bounce/error.

`deals.amount` — чистая сумма продавцу. При комиссии `0.01` сделка на 100 TON
требует от покупателя ровно 101 TON. После подтверждения получения одна batch-транзакция
отправляет продавцу 100 TON, а весь оставшийся баланс — на `SERVICE_FEE_WALLET`
с комментарием `Service fee`. Исходящие blockchain fees вычитаются из сервисного остатка.
При резерве `0.01 TON` и комиссии 1% минимальная сумма сделки равна `1 TON`:
меньшая комиссия не гарантирует выплату продавцу после развёртывания subwallet.

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

Заполните `.env`, затем примените в Supabase по порядку:
`app/database/schema.sql` и `app/database/routines.sql`.

### 2. Запустить приложение

```bash
python -m app.main
```

По умолчанию бот использует long polling, а FastAPI слушает
`http://0.0.0.0:8000`.

### 3. Проверить состояние

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/ping
curl http://localhost:8000/readyz
```

- `/healthz` проверяет, что HTTP-процесс работает;
- `/ping` — лёгкий endpoint для внешнего Render keep-alive monitor;
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
`.gitignore`. Для Render используйте полный безопасный шаблон
`render.env.example`: публичные значения уже заполнены, а секреты отмечены
`REPLACE_WITH_...`.

### Обязательные секреты

| Переменная | Назначение |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather. |
| `SUPABASE_URL` | URL проекта вида `https://PROJECT.supabase.co`. |
| `SUPABASE_KEY` | Серверный Supabase secret key либо legacy `service_role`; не anon/publishable key. |
| `TON_MNEMONIC` | 24 слова выделенного кошелька гаранта. Управляет реальными средствами. |
| `TON_GUARANT_ADDRESS` | Ожидаемый default WalletV5R1-адрес этой мнемоники в выбранной сети. |

### Приложение и Telegram

| Переменная | По умолчанию | Описание |
|---|---:|---|
| `APP_NAME` | `Gift Guarant` | Имя FastAPI-приложения. |
| `APP_HOST` | `0.0.0.0` | Интерфейс HTTP-сервера. На Render не менять. |
| `APP_PORT` | `8000` | Порт Uvicorn; на Render задать `10000`. |
| `APP_BASE_URL` | пусто | Публичный HTTPS URL, обязателен в webhook-режиме. |
| `RENDER_EXTERNAL_URL` | пусто | Публичный URL, автоматически выдаётся Render. Вручную обычно не задаётся. |
| `RENDER_KEEPALIVE_ENABLED` | `false` | Включает исходящий self-ping публичного `/ping`. Blueprint задаёт `true`. |
| `RENDER_KEEPALIVE_INTERVAL_SECONDS` | `600` | Интервал self-ping: 600 секунд = 10 минут. |
| `RENDER_KEEPALIVE_TIMEOUT_SECONDS` | `10` | Timeout одного keep-alive запроса. |
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
| `TON_GUARANT_ADDRESS` | — | Контрольный default WalletV5R1-адрес (`subwallet_number=0`); при несовпадении seed/сети запуск блокируется. |
| `TON_NETWORK` | `mainnet` | `mainnet` или `testnet`; сеть должна совпадать с endpoint. |
| `TON_WORKCHAIN` | `0` | Workchain создаваемых адресов. |
| `TON_REQUEST_TIMEOUT_MS` | `15000` | Timeout HTTP-запросов к TON API. |
| `TON_TRANSFER_TTL_SECONDS` | `60` | Срок действия подписанного сообщения выплаты. |
| `TON_TRACE_GRACE_SECONDS` | `120` | Время ожидания появления trace после отправки. |
| `TON_TRANSACTION_SCAN_LIMIT` | `50` | Число последних транзакций для проверки оплаты. |
| `SERVICE_FEE_WALLET` | — | TON-адрес получения сервисной комиссии после выплаты продавцу. |
| `SERVICE_FEE_COMMENT` | `Service fee` | Текстовый комментарий перевода сервисной комиссии. |
| `TON_PAYOUT_FEE_RESERVE` | `0.01` | Минимальная часть комиссии в TON, резервируемая под deploy и исходящие fees. |

### Сделки и фоновые задачи

| Переменная | По умолчанию | Описание |
|---|---:|---|
| `DEAL_POLL_INTERVAL_SECONDS` | `15` | Интервал проверки платежей и выплат. |
| `DEAL_PAYMENT_TIMEOUT_SECONDS` | `900` | Время на оплату присоединённой сделки. |
| `FAILED_DEAL_RETENTION_DAYS` | `30` | Хранение неуспешных сделок, допустимо 1–30 дней. |
| `RETENTION_CLEANUP_INTERVAL_SECONDS` | `86400` | Интервал запуска очистки. |
| `ESCROW_FEE_RATE` | `0.01` | Комиссия гаранта: `0.01` = 1%. |
| `REFERRAL_FEE_SHARE` | `0.01` | Реферальная доля: `0.01` = 1%. |
| `AUTO_PAYOUT_AFTER_PAYMENT` | `false` | Защитный инвариант escrow; значение `true` запрещено конфигурацией. |
| `DEALS_PAGE_SIZE` | `8` | Количество сделок на странице. |
| `DEFAULT_LANGUAGE` | `ru` | Язык нового пользователя: `ru` или `en`. |
| `DEFAULT_CURRENCY` | `TON` | Рабочая валюта; сейчас поддерживается только `TON`. |

## Supabase

### Первичная настройка

1. Создайте проект Supabase и откройте `SQL Editor`.
2. Выполните весь файл `app/database/schema.sql` одним запуском.
3. Затем выполните весь файл `app/database/routines.sql` одним запуском.
4. В `Project Settings -> API Keys` получите server-side secret key. Если проект
   использует старые ключи, допустим legacy `service_role`.
5. Запишите URL и ключ в `SUPABASE_URL` и `SUPABASE_KEY`.
6. Запустите приложение и проверьте `/readyz` и логи старта.

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

Бот использует одну мнемонику и отдельный контракт кошелька для каждой сделки.
Указанный `TON_GUARANT_ADDRESS` — default WalletV5R1 с `subwallet_number=0`.
Он служит контрольной идентичностью seed и намеренно не используется как общий
горячий баланс. При старте адрес заново выводится из мнемоники, сети и workchain;
несовпадение останавливает приложение до доступа к средствам.

Новые сделки создаются на WalletV5R1 с номеров `1..32767`; номер `0`
зарезервирован за адресом гаранта. Таблица `deals` хранит пару
`(wallet_version, subwallet_id)`, потому что версия контракта является частью
адреса и должна использоваться при каждом восстановлении кошелька.

Для обычного клиентского контекста Wallet V5R1 `subwallet_id` в проекте означает
15-битный `subwallet_number`. Из него, workchain, версии и global ID
сети формируется 32-битный `wallet_id`. Mainnet и testnet поэтому дают разные
адреса даже при одинаковой мнемонике и номере.

SQL-миграция безопасно помечает все уже существующие сделки как `v4r2`, а новые
строки по умолчанию создаёт как `v5r1`. Старые строки нельзя вручную переводить
в `v5r1`: это вычислит другой адрес и лишит приложение доступа к средствам
исходного V4R2-контракта. Уже созданная историческая сделка с номером `0`
сохраняет адрес, но последовательность больше его не выдаёт. Для новых сделок
доступно 32767 V5-адресов; при исчерпании последовательности создание
новой сделки завершится ошибкой вместо повторного использования адреса.

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
6. Сумма покупателя равна `deals.amount + 1%`. До нажатия покупателем
   «Подтвердить получение» средства остаются на escrow-subwallet сделки.
   Продавцу перечисляется ровно
   `deals.amount`, затем send mode `128` переводит весь оставшийся баланс на
   `SERVICE_FEE_WALLET` с комментарием `Service fee`. Поэтому исходящие blockchain fees
   уменьшают комиссию сервиса, а не выплату продавцу.
7. При комиссии 1% и `TON_PAYOUT_FEE_RESERVE=0.01` бот принимает сделки от
   `1 TON`. Перед подписью BOC резерв проверяется повторно; небезопасная выплата
   блокируется без отправки средств.

Эта схема соответствует варианту unique deposit address из официальной
[документации обработки TON-платежей](https://docs.ton.org/applications/payments/gram).
Разные subwallet имеют независимые адреса, балансы и `seqno`; одна мнемоника
даёт боту право подписи, но не объединяет их средства. Общий hot wallet здесь
не используется, чтобы одна ошибка или конкурирующая выплата не затронула весь
пул сделок.

Платёж засчитывается только при одновременном совпадении destination, точной
суммы в nanoTON, memo/public ID, credit phase и отсутствии bounce. Первый
неbounceable перевод на ещё не развёрнутый WalletV4R2/WalletV5R1 переводит адрес из
`nonexist` в `uninit`: compute phase может быть пропущен, но TON остаются на
балансе. Поэтому входящий платёж проверяется по фактическому credit phase, а не
отбрасывается только из-за флага `aborted`. См. официальную документацию:
[статусы аккаунта](https://docs.ton.org/foundations/status),
[internal messages](https://docs.ton.org/foundations/messages/internal) и
  [форматы адресов](https://docs.ton.org/foundations/addresses/formats) и
  [Wallet V5](https://docs.ton.org/contracts/standard/wallets/v5).

TON-транзакция содержит входящее сообщение с адресами отправителя и получателя,
значением перевода и телом сообщения. Текстовый комментарий — это payload с
32-битным нулевым opcode и UTF-8 текстом. Поэтому бот может и должен проверять
адрес сделки, точную сумму и memo одновременно. Проверка только memo небезопасна:
один и тот же комментарий можно скопировать в перевод на другой адрес или
использовать при недоплате. После подтверждения продавец получает ссылку
Tonviewer на сохранённый `paid_tx_hash`, чтобы независимо увидеть платёж.

Выплата считается завершённой только после успешного TonAPI trace, а не сразу
после broadcast.

## Render Deploy

Проект разворачивается как Docker Web Service — Dockerfile уже закрепляет
CPython 3.14.3.

1. Загрузите проект в приватный Git-репозиторий без `.env`.
2. Создайте Blueprint из `render.yaml` либо выберите `New -> Web Service`.
3. При ручной настройке укажите `Language: Docker`, нужную branch и корень, где
   лежит `Dockerfile`.
4. Выберите **один** экземпляр сервиса. Несколько экземпляров одновременно
   запустят несколько polling/retention циклов.
5. В `Environment` добавьте переменные из `.env.example` и секреты.
6. Обязательно задайте `APP_HOST=0.0.0.0` и `APP_PORT=10000`.
7. В `Health Check Path` укажите `/healthz`; Blueprint задаёт его автоматически.
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
В `render.yaml` включён `RenderKeepAlive`: процесс сразу после старта и затем раз в 10 минут
обращается к автоматически выданному `RENDER_EXTERNAL_URL/ping`. Запрос
выполняется в отдельном thread через стандартную библиотеку и не блокирует
Aiogram, FastAPI или TON monitor.

Self-ping не может восстановить уже остановленный процесс и не защищает от
перезапуска платформы. Поэтому дополнительно настройте внешний монитор:

Настройте внешний монитор на:

```text
GET https://SERVICE.onrender.com/ping
Interval: 10 minutes
Expected status: 200
```

Пинг раз в 15 минут находится на границе тайм-аута и ненадёжен. Внешний и внутренний
мониторы используют 10 минут. Подробнее:
[uptime best practices](https://render.com/docs/uptime-best-practices) и
[ограничения Free](https://render.com/docs/free).

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
| Supabase возвращает RLS/permission error | Используется ли server secret/service-role key, применены ли `schema.sql` и все GRANT из `routines.sql`. |
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

## Какие данные нужны для запуска

Секреты не нужно отправлять разработчику или публиковать в Git. Добавьте их
самостоятельно в Render `Environment`:

| Данные | Переменная | Где получить |
|---|---|---|
| Telegram bot token | `TELEGRAM_BOT_TOKEN` | BotFather для `@GiftGuarantBot`. |
| Telegram username | `TELEGRAM_BOT_USERNAME` | `GiftGuarantBot`, без `@`. |
| Supabase project URL | `SUPABASE_URL` | Supabase Project Settings. |
| Supabase server secret | `SUPABASE_KEY` | Secret key или legacy `service_role`, не anon key. |
| TonAPI key | `TON_API_KEY` | TON Console; нужен для стабильных лимитов polling. |
| Выделенная TON-мнемоника | `TON_MNEMONIC` | Новый отдельный seed из 24 слов; новые сделки используют WalletV5R1, старые сохраняют WalletV4R2. |
| Контрольный адрес гаранта | `TON_GUARANT_ADDRESS` | Default WalletV5R1-адрес мнемоники для выбранной сети, subwallet number `0`. |
| Кошелёк комиссии | `SERVICE_FEE_WALLET` | Адрес, на который batch-перевод отправляет остаток с комментарием `Service fee`. |
| Сеть | `TON_NETWORK` | Сначала `testnet`, после полного теста — `mainnet`. |
| Поддержка | `SUPPORT_USERNAME` | Telegram username поддержки. |

До финального повторения визуала `@GiftGuarantBot` дополнительно нужны скриншоты
или запись полного пользовательского пути: `/start`, главное меню, создание
сделки, карточка продавца/покупателя, настройки, профиль, ошибки и успешная
выплата. Для бизнес-логики ещё нужно подтвердить минимальную/максимальную
сумму, время оплаты, реферальный процент и необходимость
автоматического refund при неверной сумме.
