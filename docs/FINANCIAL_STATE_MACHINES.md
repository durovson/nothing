# Financial state machines

## Сделка

```text
creating ──wallet derived──> pending
    └──failure─────────────> creation_failed ──30d──> archived

pending ──cancel before payment──> cancelled ──30d, no payment──> archived
pending ──payment deadline 1h──> cancelled(timeout)
pending/cancelled ──valid payment observed──> collecting

collecting ──TON BOC submitted──> collection_submitted
collecting (USDT) / collection_submitted (TON)
    ├──custody confirmed, no dispute──> delivery_pending
    └──custody confirmed, open dispute──> disputed

delivery_pending ──seller delivered──> delivered
delivery_pending ──deadline──> refund_requested
delivered ──buyer confirms / inspection deadline──> release_requested
delivery_pending|delivered ──dispute/cancel──> disputed

disputed ──admin release──> release_requested
disputed ──admin refund──> refund_requested | refund_awaiting_wallet

release_requested ──ledger planned──> payout_processing
payout_processing ──all payout legs confirmed──> completed

refund_requested ──ledger planned──> refund_processing
refund_processing ──all refund legs confirmed──> refunded
```

После обнаружения оплаты кнопка отмены отсутствует. Запрос отмены из старого сообщения или callback создаёт `dispute_tickets`; прямой refund невозможен. Для TON во время collection статус не меняется до подтверждения custody, иначе потерялось бы наблюдение уже отправленной транзакции. Открытый тикет переводит сделку в `disputed` атомарно с фиксацией custody.

## Финансовая операция

```text
pending ──claim/lock──> pending
pending|failed|bounced ──signed BOC saved──> prepared
prepared ──broadcast same BOC──> submitted
submitted ──exact trace matched──> confirmed
submitted ──trace proves failure──> failed ──backoff──> prepared
submitted ──trace proves bounce──> bounced ──backoff──> prepared
prepared|submitted ──outcome uncertain after TTL+grace──> manual_review
failed|bounced ──six backoffs exhausted; next failure──> manual_review
manual_review ──admin reopen──> pending
manual_review ──verified tx hash + reason──> confirmed
```

Backoff: 1 минута, 5 минут, 15 минут, 1 час, 6 часов, затем 24 часа и `manual_review`. Каждый collection/seller/refund/service/referral transfer имеет собственные `operation_id`, idempotency key и immutable attempts. Batch для нового ledger не используется. Collection подписывается временным subwallet сделки; остальные операции — кошельком гаранта.

## Восстановление после сбоев

| Момент сбоя | Восстановление | Защита от дубля |
|---|---|---|
| До сохранения BOC | lease истечёт, операция будет подготовлена снова | в сети ничего не отправлено |
| После сохранения BOC, до broadcast | trace проверяется первым; затем публикуется тот же BOC | один external hash и wallet seqno |
| После broadcast, до `submitted` | проверяется trace; при необходимости публикуется тот же BOC | новый transfer не создаётся |
| TonAPI временно не видит trace | ожидание до TTL + grace | retry не выполняется |
| Результат после grace неизвестен | `manual_review` | автоматический replay запрещён |
| Один payout leg подтверждён, другой failed | повторяется только failed leg | отдельные idempotency keys |
| Процесс упал после подтверждения leg | повторный RPC идемпотентен; flow завершается только когда подтверждены все legs | `confirmed` терминален |
| Старый legacy batch | мигрируется в `manual_review` | автоматический retry legacy batch запрещён |
| Старый collection attempt | hash/BOC мигрируются в `manual_review` | неизвестный broadcast не переигрывается |

## TON и USDT deposit indexers

USDT-индексатор последовательно читает историю аккаунта гаранта, TON-индексатор — историю каждого активного временного subwallet. Сначала создаётся immutable `observed_deposits`, затем депозит либо атомарно привязывается к сделке, либо попадает в `unmatched_payments`. Проверяются актив, точная atomic-сумма, memo и snapshot sender. Неверный TON-платёж собирается на гарант через `collection_transfer`, после чего доступен контролируемый возврат наблюдаемому sender. Курсор сохраняется только после обработки batch. Повторный запуск безопасен за счёт unique `tx_hash` и `account_address + tx_lt`.

## Системные режимы

`NORMAL` разрешает все операции. `READ_ONLY` включается автоматически только после непрерывного сбоя Supabase, TonAPI, guarant health или worker heartbeat в течение 15 минут; создание и вступление в новые сделки останавливаются, но уже отправленные on-chain платежи индексируются, а collection/recovery/refund продолжаются. Автоматический режим снимается после восстановления. `EMERGENCY` меняется только администратором: payout, collection новых депозитов и referral withdrawal остановлены, refund/unmatched-refund и recovery/admin действия разрешены.

Экономика refund фиксирована: покупателю возвращается principal `D`, комиссия сервиса 1,5% удерживается, сетевой gas не возвращается. Условие отображается до оплаты и в пользовательском соглашении.
