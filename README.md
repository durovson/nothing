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

Продавец создаёт сделку и передаёт ссылку покупателю. Покупатель привязывает кошелёк, вступает и оплачивает `D + 1% + gas`. Для обычного оффера срок этапа — 1 час, для передачи канала — 24 часа. После подтверждения услуги продавец получает `D`; collection, выплата, комиссия и возврат исполняются через единый восстанавливаемый ledger. После оплаты отмена создаёт спор. При refund покупателю возвращается `D`, комиссия сервиса 1% удерживается; это явно показано до оплаты.

Точные state-machine сделки, финансовой операции и сценарии восстановления описаны в [`docs/FINANCIAL_STATE_MACHINES.md`](docs/FINANCIAL_STATE_MACHINES.md).

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

Проверки: `GET /healthz`, `GET /readyz`, `GET /ping`. Они реально проверяют Supabase, TonAPI, Telegram и каждый финансовый worker; при деградации возвращается HTTP 503.

Тесты:

```powershell
python -m unittest discover -s tests -v
```

## Supabase

Для новой базы выполните в SQL Editor по порядку:

1. `app/database/schema.sql`
2. `app/database/routines.sql`
3. `app/database/lifecycle.sql`
4. `app/database/permissions.sql`
5. все файлы из `app/database/migrations` в порядке имени, включая `20260728_financial_ledger.sql`, `20260729_operational_safety.sql`, `20260730_worker_and_deadline_safety.sql` и `20260731_completed_deal_feed.sql`

Для уже работающей базы дополнительно примените миграции в порядке имени. Для этого обновления обязательны:

1. `app/database/migrations/20260728_navigation_notifications.sql`
2. `app/database/migrations/20260728_cancellation_flow.sql`
3. `app/database/migrations/20260728_wallet_snapshots.sql`
4. `app/database/migrations/20260728_financial_ledger.sql`
5. `app/database/migrations/20260729_operational_safety.sql`
6. `app/database/migrations/20260730_worker_and_deadline_safety.sql`
7. `app/database/migrations/20260731_completed_deal_feed.sql`

Ledger-миграция безопасно добавляет независимые collection/payout/refund/referral операции, attempts, TON/USDT cursor,
`observed_deposits`, `unmatched_payments`, архивирование и явный `buyer_wallet_snapshot`.
Старые незавершённые collection и batch-attempts переносятся в `manual_review` и не повторяются автоматически.
Финансовая история и сделки с движением средств не удаляются.

`SUPABASE_KEY` должен быть серверным `service_role`/secret key. Его нельзя публиковать в GitHub или передавать клиенту.

## TON

- `TON_MNEMONIC` — ровно 24 слова кошелька гаранта.
- `TON_GUARANT_ADDRESS` обязан соответствовать этой mnemonic и выбранной сети.
- Для USDT используется официальный master-адрес из `USDT_MASTER_ADDRESS`.
- На кошельке гаранта должен быть TON для gas, включая USDT jetton transfer.
- Проверка оплаты использует адрес, актив, сумму и memo; один комментарий не считается достаточным доказательством.
- USDT индексируется последовательно по TEP-74 notification, а TON — отдельно для каждого временного subwallet. Неправильная сумма, memo или sender сохраняются в `unmatched_payments` и видны администратору.
- Collection временного TON-кошелька, seller/refund/service/referral transfer имеют отдельные immutable attempts и подтверждаются своим trace.
- Неверный TON-платёж сначала собирается на гарант через collection-ledger; только затем администратор может вернуть его наблюдаемому sender.

## Режимы безопасности

- `NORMAL` — доступны все операции.
- `READ_ONLY` — автоматически включается после непрерывного отказа инфраструктуры 15 минут; просмотр остаётся доступен, интерфейс новых сделок и платежей запрещён. Уже отправленные on-chain платежи продолжают индексироваться, а collection/recovery/refund — исполняться. После устойчивого восстановления режим снимается автоматически.
- `EMERGENCY` — включается только администратором кнопкой или `/emergency on`. Запрещены новые сделки, депозиты, payout и referral withdrawal; разрешены refund, recovery и админские действия. Отключение: `/emergency off`.

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

Полный безопасный шаблон находится в `.env.example`. Фиксированные бизнес-параметры: комиссия сервиса `1%`, минимум GRAM/TON `1`, минимум USDT `1`, этап обычного оффера — один час, передача канала — 24 часа, максимум пять сделок на странице, хранение неуспешных сделок до 30 дней.

Никогда не коммитьте `.env`, Telegram token, Supabase secret, TonAPI key или mnemonic. Если секрет уже публиковался, его необходимо отозвать и выпустить заново.

## Юридические документы

Публичные страницы находятся в `app/assets/documents`:

- `privacy.html` — политика конфиденциальности и обработки персональных данных;
- `terms.html` — пользовательское соглашение;
- `service.html` — полное описание и условия сервиса.

Перед публичным запуском обязательно замените все поля `[ЗАПОЛНИТЬ ...]` и `[... E-MAIL]` реальными данными Оператора, укажите применимое право и сроки хранения, проверьте регионы Render/Supabase и требования локализации. Нельзя публиковать шаблон как окончательную оферту без наименования, адреса и регистрационных реквизитов Оператора. Необходимо получить отдельное заключение юриста о допустимости custodial escrow цифровых активов в выбранной юрисдикции. Для работы с резидентами РФ отдельно проверить ограничения 259-ФЗ, требования 115-ФЗ, статус оператора электронной площадки/посредника, налогообложение и допустимость расчётов цифровой валютой за товары, работы и услуги.
