# Gift Guarant

Production-oriented Telegram escrow bot for native TON (displayed to users as GRAM) and official USDT on TON. The bot holds funds on the central guarant wallet until the buyer confirms delivery, an SLA expires, or an administrator resolves a dispute.

## Stack

- CPython 3.14.3
- Aiogram 3.30.0
- FastAPI 0.139.2 and Uvicorn 0.51.0
- Supabase 2.31.0 / PostgreSQL
- Pydantic 2.13.4 and pydantic-settings 2.14.2
- tonutils 2.1.0 and TonAPI

Versions are pinned in `requirements.txt`.

## Architecture

```text
app/
├── api/           FastAPI lifecycle, health checks and Render keep-alive
├── core/          enums, constants, protocols, exceptions and logging
├── database/      schema, RLS and security-definer RPCs
├── handlers/      thin Aiogram controllers, including isolated admin router
├── keyboards/     typed CallbackData and payment buttons
├── middleware/    current user and persistent maintenance gate
├── models/        domain entities and DTOs
├── repositories/  the only Supabase access layer
├── services/      business rules, admin operations and money lifecycle
├── tasks/         payment, collection, SLA, refund and payout loops
└── ton/           tonutils gateway and strict TON/TEP-74 trace validation
```

Handlers do not access Supabase or TON. Services receive dependencies from `app/loader.py`. Repositories contain persistence only.

## Money model

`D` is the seller’s price.

### TON

```text
Buyer invoice: D + 1% + 0.01 TON network reserve
Release:       seller D; service wallet 1%
Refund:        buyer D; service wallet 1%
```

The network reserve covers collection and central-wallet transfers. It is not a service profit and is not returned. The seller always receives exactly `D`.

### USDT on TON

```text
Buyer invoice: D + 1% USDT
Release:       seller D USDT; service wallet 1% USDT
Refund:        buyer D USDT; service wallet 1% USDT
```

USDT is a Jetton with 6 decimals. Its gas is paid in TON, not USDT. The payer funds the incoming Jetton transfer; the central guarant wallet must keep a working TON balance for two outgoing Jetton messages. `USDT_JETTON_TRANSFER_TON=0.05` is attached to each outgoing transfer and unused excess returns to the guarant wallet.

The official mainnet USDT master is allowlisted as `EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs`. The setting accepts no other value. Official USDT is mainnet-only.

## Payment security

- Both seller and buyer must link a TON owner address before entering the deal.
- TON uses a unique Wallet V5 subwallet per deal and then collects custody to central Wallet V5 subwallet 0.
- USDT goes directly to the central guarant owner address using an invoice comment; no unfunded temporary Jetton wallet is created.
- USDT acceptance validates the trusted master-derived Jetton wallet, TEP-74 opcode `0x7362d09c`, exact micro-USDT amount, sender and exact deal ID.
- `payment_sender` is evidence only and is never an automatic refund destination.
- Payout/refund attempts store currency, destinations, exact atomic amounts, signed BOC, normalized hash and expiry.
- A batch is confirmed only after every expected recipient notification is present.

## Payment links

At the payment stage the buyer receives an HTTPS Tonkeeper button with address, exact amount and comment. For USDT it also includes the official Jetton master.

The protocol-level `ton://transfer` scheme is interoperable for native TON. Jetton invoice support differs between wallets, so a single bot button cannot guarantee every wallet. Users of Telegram Wallet, MyTonWallet and other wallets can copy the displayed address, amount and comment. A universal wallet picker requires a Telegram Mini App with TON Connect.

## Lifecycle and disputes

```text
pending → collecting/direct custody → delivery_pending → delivered
                                                  ├→ release → completed
                                                  ├→ dispute → admin decision
                                                  └→ refund → refunded
```

- payment window: 60 minutes
- seller delivery SLA: 24 hours
- buyer inspection: 3 hours for gifts, 24 hours for accounts/channels
- seller silence: automatic refund
- buyer silence after delivery: automatic release
- an open dispute freezes automatic resolution

Dispute descriptions contain 10–1000 characters. Screenshots are not stored; parties send evidence directly to support.

## Admin panel

Send `/admin`. Access is restricted to comma-separated `ADMIN_IDS`; default: `786080766`.

The panel provides:

1. paginated disputes, open tickets first; ticket/deal details; release or refund with a mandatory reason
2. broadcast of any Telegram content type by copying the source message to all users
3. persistent maintenance mode; only administrators can use the bot while it is enabled

Admin decisions call the same atomic server-side RPCs as automated flows. They do not send funds directly from handlers.

## Supabase installation

Run the files completely and in this exact order in SQL Editor:

1. `app/database/schema.sql`
2. `app/database/routines.sql`
3. `app/database/lifecycle.sql`
4. `app/database/permissions.sql`

Use only a server-side service-role/secret key. `permissions.sql` enables RLS and grants financial/admin RPC execution only to `service_role`.

## Local run

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.main
```

Health endpoints: `/ping`, `/healthz`, `/readyz`.

Supabase SELECT requests are serialized through one shared client and retried up to three times after transient `httpx/httpcore` transport failures. Mutating requests and financial RPCs are never blindly replayed; their idempotent background workflow reconciles them on the next iteration.

## Render deploy

Deploy one Docker Web Service using `render.yaml`, with health check `/healthz`. The built-in keep-alive calls `APP_BASE_URL/ping` every 840 seconds. A sleeping free instance cannot wake itself; use an external uptime monitor or an always-on Render plan.

Minimal Render variables:

```dotenv
APP_PORT=10000
APP_BASE_URL=https://YOUR-SERVICE.onrender.com
TELEGRAM_USE_POLLING=true
TELEGRAM_BOT_USERNAME=YOUR_BOT
SUPPORT_USERNAME=@YOUR_SUPPORT
ADMIN_IDS=786080766
TELEGRAM_BOT_TOKEN=SECRET
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_KEY=SECRET_SERVICE_ROLE
TON_API_KEY=SECRET
TON_MNEMONIC=SECRET_24_WORDS
TON_GUARANT_ADDRESS=MATCHING_V5R1_SUBWALLET_0_ADDRESS
SERVICE_FEE_WALLET=TON_OWNER_ADDRESS
USDT_MASTER_ADDRESS=EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs
MIN_USDT_DEAL_AMOUNT=1
```

Enter keys and values in separate Render fields. Do not paste `KEY=VALUE`, Markdown links, or surrounding quotes into a value.

## Official TON references

- [TON deep links](https://docs.ton.org/onboarding/wallet-apps/deep-links)
- [Jetton payment processing](https://docs.ton.org/applications/payments/jettons)
- [TON Connect send transaction](https://docs.ton.org/applications/ton-connect/how-to/send-transaction)
- [Wallet V5](https://docs.ton.org/contracts/standard/wallets/v5)
- [TEP-74 Jetton standard](https://github.com/ton-blockchain/TEPs/blob/master/text/0074-jettons-standard.md)

## Secrets

`.env`, mnemonic, Telegram token, Supabase secret and TonAPI key are excluded from Git/Docker/ZIP. Rotate every secret that has ever been pasted into chat or logs. Change the mnemonic only after reconciling and moving funds from all derived old wallets.
