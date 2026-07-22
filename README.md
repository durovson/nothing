# Gift Guarant

Production-oriented Telegram escrow bot built for CPython 3.14.3, Aiogram 3.x,
FastAPI, Supabase/PostgreSQL and TON WalletV4R2.

## Architecture

```text
app/
├── main.py                 process entrypoint
├── loader.py               composition root; the only dependency assembly point
├── bot.py                  Aiogram Dispatcher factory
├── config.py               validated environment settings
├── api/                    FastAPI routes/lifecycle and Telegram notification adapter
├── core/                   enums, constants, exceptions, Protocol contracts, logging
├── database/               Supabase adapter and PostgreSQL schema/RPC
├── handlers/               thin Telegram input/output adapters
├── keyboards/              typed CallbackData and feature keyboards
├── locales/                typed translation catalog
├── middleware/             current-user transport context
├── models/                 domain entities and application DTO
├── repositories/           users, deals, payouts and referrals persistence adapters
├── services/               application business use cases
├── states/                 Aiogram FSM states
├── tasks/                  payment, payout and retention loops
└── ton/                    TON client, parsing, amounts and transport DTO
```

Dependency direction is fixed:

```text
handlers / middleware / API / tasks
                  ↓
               services
                  ↓
          core Protocol contracts
                  ↑
 repositories / TON / Telegram notifier
```

- Handlers validate Telegram input, call a service and render a response.
- Services contain business use cases and do not import Aiogram, Supabase or SQL.
- Every Supabase call lives in a repository; the synchronous SDK is isolated by
  `SupabaseDatabase.run()` using `asyncio.to_thread`.
- TON SDK details live only in `app/ton`.
- Dependencies are injected through constructors and assembled in `app/loader.py`.
- Callback payloads use Aiogram `CallbackData`; no string parsing or f-string
  callback protocol is used.

## Payment and payout invariants

Each deal has a unique persisted `subwallet_id` and therefore a separate
WalletV4R2 address. `deals.amount` is the net seller amount; the buyer pays the
amount plus the configured service fee. For example, 870 TON produces a 896.1
TON incoming payment and an 870 TON seller payout.

An incoming payment is accepted only when destination, exact atomic amount,
memo/public deal ID and non-bounced transaction state all match. PostgreSQL RPC
functions atomically claim a payment and the single payout attempt.

The signed payout BOC and normalized external-message hash are stored before
broadcast. Reconciliation then resolves the TonAPI trace to confirmed, bounced
or failed. A bounced payout is never marked completed.

## Retention

Pending joined deals expire after the configured payment window (900 seconds by
default). Unsuccessful terminal deals — `cancelled`, `creation_failed`,
`payout_failed`, `payout_bounced` — are deleted by a protected RPC after at most
30 days. Successful deals and users are retained.

## Installation

1. Install CPython 3.14.3 and dependencies:

   ```bash
   python3.14 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill secrets. `SUPABASE_KEY` must be the
   server-side service-role key, never the anon key.
3. Apply `app/database/schema.sql` in the Supabase SQL editor.
4. Start the application:

   ```bash
   .venv/bin/python -m app.main
   ```

On Windows use `.venv\\Scripts\\python.exe`. The Docker image is pinned to
`python:3.14.3-slim` and runs as an unprivileged user.

For webhook mode set `TELEGRAM_USE_POLLING=false`, `APP_BASE_URL` and a random
`TELEGRAM_WEBHOOK_SECRET`. Endpoints are `/healthz`, `/readyz` and the configured
Telegram webhook path.

## USDT

`USDT_TON` remains intentionally disabled in the creation UI and rejected by the
service until a jetton-specific deposit and payout implementation is added.
Treating jetton USDT as native TON would be unsafe.
