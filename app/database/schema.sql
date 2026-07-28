begin;
create sequence if not exists deal_subwallet_id_seq
    as bigint minvalue 100000 maxvalue 4294967295 start with 100000 no cycle;
create sequence if not exists deal_wallet_v5_subwallet_seq
    as bigint minvalue 1 maxvalue 32767 start with 1 no cycle;

create table if not exists users (
    telegram_id bigint primary key,
    username text,
    wallet_address text,
    language text not null default 'ru',
    referrer_id bigint references users(telegram_id) on delete set null,
    created_at timestamptz not null default timezone('utc', now())
);

alter table users drop constraint if exists users_language_check;
alter table users add constraint users_language_check check (language in ('ru', 'en'));
create table if not exists deals (
    id bigint generated always as identity primary key,
    public_id text not null unique,
    subwallet_id bigint not null,
    wallet_version text not null default 'v5r1',
    creator_id bigint not null references users(telegram_id) on delete cascade,
    buyer_id bigint references users(telegram_id) on delete set null,
    deal_type text not null check (deal_type in ('offer', 'gifts', 'channel', 'account')),
    description text not null,
    currency text not null check (currency in ('TON', 'USDT')),
    amount numeric(36, 9) not null check (amount > 0),
    status text not null default 'creating',
    wallet_address text,
    paid_tx_hash text,
    paid_tx_lt numeric(20, 0),
    paid_amount_atomic numeric(30, 0),
    payment_sender text,
    payment_memo_missing boolean not null default false,
    paid_at timestamptz,
    failure_reason text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

-- Safe upgrade path for the original schema.
alter table deals add column if not exists public_id text;
alter table deals add column if not exists subwallet_id bigint;
alter table deals add column if not exists wallet_version text;
alter table deals add column if not exists paid_tx_hash text;
alter table deals add column if not exists paid_tx_lt numeric(20, 0);
alter table deals add column if not exists paid_amount_atomic numeric(30, 0);
alter table deals add column if not exists payment_sender text;
alter table deals add column if not exists payment_memo_missing boolean not null default false;
alter table deals add column if not exists paid_at timestamptz;
alter table deals add column if not exists failure_reason text;
alter table deals add column if not exists custody_confirmed_at timestamptz;
alter table deals add column if not exists delivery_deadline_at timestamptz;
alter table deals add column if not exists delivered_at timestamptz;
alter table deals add column if not exists inspection_deadline_at timestamptz;
alter table deals add column if not exists resolution text;
alter table deals add column if not exists resolution_reason text;
alter table deals add column if not exists updated_at timestamptz not null default timezone('utc', now());
alter table deals add column if not exists channel_id bigint;
alter table deals add column if not exists channel_title text;
alter table deals add column if not exists channel_username text;
alter table deals add column if not exists channel_access_granted_at timestamptz;
alter table deals add column if not exists channel_access_error text;
alter table deals add column if not exists channel_owner_verified_at timestamptz;
alter table deals add column if not exists channel_last_member_status text;
alter table deals add column if not exists channel_last_checked_at timestamptz;
alter table deals add column if not exists buyer_join_notified_at timestamptz;
alter table deals add column if not exists cancellation_requested_at timestamptz;

update deals
set public_id = substring(md5(id::text || clock_timestamp()::text || random()::text), 1, 10)
where public_id is null;

update deals
set subwallet_id = 100000 + id
where subwallet_id is null;

-- Every row that existed before Wallet V5 support owns a V4R2 address.
-- Never re-label these rows: the wallet version is part of the address.
update deals
set wallet_version = 'v4r2'
where wallet_version is null;

select setval(
    'deal_subwallet_id_seq',
    greatest(100000, coalesce((select max(subwallet_id) + 1 from deals), 100000)),
    false
);

do $$
declare
    v_next bigint;
begin
    select greatest(1, coalesce(max(subwallet_id) + 1, 1))
    into v_next
    from deals
    where wallet_version = 'v5r1';

    if v_next <= 32767 then
        perform setval('deal_wallet_v5_subwallet_seq', v_next, false);
    else
        perform setval('deal_wallet_v5_subwallet_seq', 32767, true);
    end if;
end;
$$;

-- Wallet V5 subwallet number 0 is the configured guarant identity wallet.
-- Existing deal rows keep their immutable address, but no new deal may reuse it.
alter sequence deal_wallet_v5_subwallet_seq minvalue 1 start with 1;

alter table deals alter column public_id set not null;
alter table deals alter column subwallet_id drop default;
alter table deals alter column subwallet_id set not null;
alter table deals alter column wallet_version set default 'v5r1';
alter table deals alter column wallet_version set not null;
create unique index if not exists deals_public_id_uidx on deals(public_id);
drop index if exists deals_subwallet_id_uidx;
alter table deals drop constraint if exists deals_subwallet_id_key;
create unique index if not exists deals_wallet_identity_uidx
    on deals(wallet_version, subwallet_id);
create unique index if not exists deals_paid_tx_hash_uidx on deals(paid_tx_hash) where paid_tx_hash is not null;

alter table deals drop constraint if exists deals_wallet_version_check;
alter table deals add constraint deals_wallet_version_check
    check (wallet_version in ('v4r2', 'v5r1'));
alter table deals drop constraint if exists deals_subwallet_id_check;
alter table deals drop constraint if exists deals_wallet_identity_check;
alter table deals add constraint deals_wallet_identity_check check (
    (wallet_version = 'v4r2' and subwallet_id between 0 and 4294967295)
    or
    (wallet_version = 'v5r1' and subwallet_id between 0 and 32767)
);
alter table deals drop constraint if exists deals_public_id_format_check;
alter table deals add constraint deals_public_id_format_check
    check (public_id ~ '^[A-Za-z0-9_-]{10,32}$');
alter table deals drop constraint if exists deals_description_length_check;
alter table deals add constraint deals_description_length_check
    check (char_length(btrim(description)) between 1 and 2000);
alter table deals drop constraint if exists deals_deal_type_check;
alter table deals add constraint deals_deal_type_check
    check (deal_type in ('offer', 'gifts', 'channel', 'account'));
alter table deals drop constraint if exists deals_channel_metadata_check;
alter table deals add constraint deals_channel_metadata_check check (
    deal_type <> 'channel'
    or (channel_id is not null and nullif(btrim(channel_title), '') is not null)
) not valid;
alter table deals drop constraint if exists deals_channel_access_error_length_check;
alter table deals add constraint deals_channel_access_error_length_check
    check (channel_access_error is null or char_length(channel_access_error) <= 1000);
alter table deals drop constraint if exists deals_channel_member_status_check;
alter table deals add constraint deals_channel_member_status_check check (
    channel_last_member_status is null
    or channel_last_member_status in ('creator', 'administrator', 'member', 'absent', 'unknown')
);
alter table deals drop constraint if exists deals_failure_reason_length_check;
alter table deals add constraint deals_failure_reason_length_check
    check (failure_reason is null or char_length(failure_reason) <= 1000);
alter table deals drop constraint if exists deals_paid_amount_check;
alter table deals add constraint deals_paid_amount_check
    check (paid_amount_atomic is null or paid_amount_atomic > 0);
alter table deals drop constraint if exists deals_currency_check;
alter table deals add constraint deals_currency_check check (currency in ('TON', 'USDT')) not valid;
alter table deals drop constraint if exists deals_status_check;
alter table deals add constraint deals_status_check check (
    status in (
        'creating', 'pending', 'collecting', 'collection_submitted',
        'collection_failed', 'paid', 'delivery_pending', 'delivered', 'disputed',
        'release_requested', 'payout_processing',
        'payout_submitted', 'payout_failed', 'payout_bounced', 'completed',
        'refund_awaiting_wallet', 'refund_requested', 'refund_processing',
        'refund_submitted', 'refund_failed', 'refund_bounced', 'refunded',
        'cancelled', 'creation_failed'
    )
);

create or replace function assign_deal_wallet_identity()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    if new.subwallet_id is not null then
        if new.wallet_version = 'v5r1' and new.subwallet_id = 0 then
            raise exception 'Wallet V5 subwallet number 0 is reserved for the guarant identity';
        end if;
        return new;
    end if;

    if new.wallet_version = 'v5r1' then
        new.subwallet_id := nextval('deal_wallet_v5_subwallet_seq');
    elsif new.wallet_version = 'v4r2' then
        new.subwallet_id := nextval('deal_subwallet_id_seq');
    else
        raise exception 'unsupported wallet version: %', new.wallet_version;
    end if;
    return new;
end;
$$;

drop trigger if exists deals_assign_wallet_identity on deals;
create trigger deals_assign_wallet_identity
before insert on deals
for each row
execute function assign_deal_wallet_identity();

create table if not exists deal_payments (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete restrict,
    tx_hash text not null unique,
    tx_lt numeric(20, 0) not null,
    amount_atomic numeric(30, 0) not null check (amount_atomic > 0),
    sender text,
    observed_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (deal_id, tx_lt)
);
create unique index if not exists deal_payments_deal_uidx on deal_payments(deal_id);

create table if not exists collection_attempts (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete restrict,
    idempotency_key text not null unique,
    status text not null check (status in ('creating', 'prepared', 'submitted', 'confirmed', 'bounced', 'failed')),
    destination text not null,
    comment text not null,
    external_message_hash text unique,
    signed_boc text,
    valid_until timestamptz,
    submitted_at timestamptz,
    confirmed_at timestamptz,
    last_checked_at timestamptz,
    error text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    unique (deal_id)
);
alter table collection_attempts drop constraint if exists collection_attempts_error_length_check;
alter table collection_attempts add constraint collection_attempts_error_length_check
    check (error is null or char_length(error) <= 1000);
create index if not exists collection_attempts_status_idx on collection_attempts(status);

create table if not exists payout_attempts (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete restrict,
    idempotency_key text not null unique,
    status text not null check (status in ('creating', 'prepared', 'submitted', 'confirmed', 'bounced', 'failed')),
    destination text not null,
    amount_atomic numeric(30, 0) not null check (amount_atomic > 0),
    comment text not null,
    reward_destination text,
    reward_nominal_amount_atomic numeric(30, 0),
    reward_comment text,
    currency text not null default 'TON',
    external_message_hash text unique,
    signed_boc text,
    valid_until timestamptz,
    submitted_at timestamptz,
    confirmed_at timestamptz,
    last_checked_at timestamptz,
    error text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

alter table payout_attempts add column if not exists reward_destination text;
alter table payout_attempts add column if not exists reward_nominal_amount_atomic numeric(30, 0);
alter table payout_attempts add column if not exists reward_comment text;
alter table payout_attempts add column if not exists currency text not null default 'TON';
alter table payout_attempts drop constraint if exists payout_attempts_currency_check;
alter table payout_attempts add constraint payout_attempts_currency_check check (currency in ('TON', 'USDT'));
create unique index if not exists payout_attempts_deal_uidx on payout_attempts(deal_id);
alter table payout_attempts drop constraint if exists payout_attempts_error_length_check;
alter table payout_attempts add constraint payout_attempts_error_length_check
    check (error is null or char_length(error) <= 1000);
alter table payout_attempts drop constraint if exists payout_attempts_reward_check;
alter table payout_attempts add constraint payout_attempts_reward_check check (
    (
        reward_destination is null
        and reward_nominal_amount_atomic is null
        and reward_comment is null
    )
    or
    (
        reward_destination is not null
        and reward_nominal_amount_atomic > 0
        and reward_comment is not null
        and char_length(btrim(reward_comment)) between 1 and 120
    )
);

create table if not exists refund_attempts (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete restrict,
    idempotency_key text not null unique,
    status text not null check (status in ('creating', 'prepared', 'submitted', 'confirmed', 'bounced', 'failed')),
    destination text not null,
    amount_atomic numeric(30, 0) not null check (amount_atomic > 0),
    comment text not null,
    reason text not null,
    currency text not null default 'TON',
    reward_destination text,
    reward_nominal_amount_atomic numeric(30, 0),
    reward_comment text,
    external_message_hash text unique,
    signed_boc text,
    valid_until timestamptz,
    submitted_at timestamptz,
    confirmed_at timestamptz,
    last_checked_at timestamptz,
    error text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    unique (deal_id)
);
alter table refund_attempts add column if not exists currency text not null default 'TON';
alter table refund_attempts add column if not exists reward_destination text;
alter table refund_attempts add column if not exists reward_nominal_amount_atomic numeric(30, 0);
alter table refund_attempts add column if not exists reward_comment text;
alter table refund_attempts drop constraint if exists refund_attempts_currency_check;
alter table refund_attempts add constraint refund_attempts_currency_check check (currency in ('TON', 'USDT'));
alter table refund_attempts drop constraint if exists refund_attempts_reward_check;
alter table refund_attempts add constraint refund_attempts_reward_check check (
    (reward_destination is null and reward_nominal_amount_atomic is null and reward_comment is null)
    or (reward_destination is not null and reward_nominal_amount_atomic > 0
        and char_length(btrim(reward_comment)) between 1 and 120)
);
alter table refund_attempts drop constraint if exists refund_attempts_text_check;
alter table refund_attempts add constraint refund_attempts_text_check check (
    char_length(btrim(comment)) between 1 and 120
    and char_length(btrim(reason)) between 1 and 1000
    and (error is null or char_length(error) <= 1000)
);

create table if not exists dispute_tickets (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete cascade,
    opened_by bigint not null references users(telegram_id) on delete restrict,
    status text not null default 'open'
        check (status in ('open', 'resolved_release', 'resolved_refund', 'closed')),
    description text not null check (char_length(btrim(description)) between 10 and 1000),
    resolution text,
    resolution_reason text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);
create unique index if not exists dispute_tickets_open_deal_uidx
    on dispute_tickets(deal_id) where status = 'open';

create table if not exists bot_settings (
    id smallint primary key check (id = 1),
    maintenance_enabled boolean not null default false,
    maintenance_message text not null default 'Технический перерыв. Попробуйте позже.',
    updated_at timestamptz not null default timezone('utc', now()),
    check (char_length(btrim(maintenance_message)) between 3 and 1000)
);
insert into bot_settings(id) values (1) on conflict (id) do nothing;

-- A legacy `paid` row without a collection record cannot prove that custody
-- reached the central guarant wallet. Block automatic release so an operator
-- can reconcile it on-chain instead of risking a payout from unrelated funds.
update deals as d
set
    status = 'collection_failed',
    failure_reason = 'Legacy paid deal requires manual custody reconciliation',
    updated_at = timezone('utc', now())
where d.status = 'paid'
  and not exists (
      select 1 from collection_attempts as c where c.deal_id = d.id
  )
  and not exists (
      select 1 from payout_attempts as p where p.deal_id = d.id
  );

update deals as d
set
    status = 'delivery_pending',
    custody_confirmed_at = coalesce(d.custody_confirmed_at, c.confirmed_at, d.updated_at),
    delivery_deadline_at = coalesce(
        d.delivery_deadline_at,
        timezone('utc', now()) + interval '24 hours'
    ),
    updated_at = timezone('utc', now())
from collection_attempts as c
where d.status = 'paid'
  and c.deal_id = d.id
  and c.status = 'confirmed';

-- Unsuccessful deals are removed by the retention RPC. Dependent financial
-- rows must be removed in the same atomic transaction.
alter table deal_payments drop constraint if exists deal_payments_deal_id_fkey;
alter table deal_payments add constraint deal_payments_deal_id_fkey
    foreign key (deal_id) references deals(id) on delete cascade;
alter table collection_attempts drop constraint if exists collection_attempts_deal_id_fkey;
alter table collection_attempts add constraint collection_attempts_deal_id_fkey
    foreign key (deal_id) references deals(id) on delete cascade;
alter table payout_attempts drop constraint if exists payout_attempts_deal_id_fkey;
alter table payout_attempts add constraint payout_attempts_deal_id_fkey
    foreign key (deal_id) references deals(id) on delete cascade;
alter table refund_attempts drop constraint if exists refund_attempts_deal_id_fkey;
alter table refund_attempts add constraint refund_attempts_deal_id_fkey
    foreign key (deal_id) references deals(id) on delete cascade;

create table if not exists referrals (
    id bigint generated always as identity primary key,
    referrer_id bigint not null references users(telegram_id) on delete cascade,
    referred_id bigint not null references users(telegram_id) on delete cascade,
    earned_ton numeric(36, 9) not null default 0,
    earned_usdt numeric(36, 6) not null default 0,
    created_at timestamptz not null default timezone('utc', now()),
    unique (referrer_id, referred_id)
);
alter table referrals add column if not exists earned_usdt numeric(36, 6) not null default 0;

alter table referrals drop constraint if exists referrals_distinct_users_check;
alter table referrals add constraint referrals_distinct_users_check
    check (referrer_id <> referred_id);
alter table referrals drop constraint if exists referrals_nonnegative_rewards_check;
alter table referrals add constraint referrals_nonnegative_rewards_check
    check (earned_ton >= 0 and earned_usdt >= 0);
create index if not exists deals_status_idx on deals(status);
create index if not exists deals_creator_idx on deals(creator_id);
create index if not exists deals_buyer_idx on deals(buyer_id);
create index if not exists payout_attempts_status_idx on payout_attempts(status);
create index if not exists refund_attempts_status_idx on refund_attempts(status);
create index if not exists deals_delivery_deadline_idx
    on deals(delivery_deadline_at) where status = 'delivery_pending';
create index if not exists deals_inspection_deadline_idx
    on deals(inspection_deadline_at) where status = 'delivered';
create index if not exists deals_channel_access_pending_idx
    on deals(id)
    where deal_type = 'channel'
      and status = 'delivery_pending'
      and channel_owner_verified_at is null
      and buyer_id is not null;
create index if not exists referrals_referrer_idx on referrals(referrer_id);

create table if not exists referral_rewards (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete restrict,
    referrer_id bigint not null references users(telegram_id) on delete restrict,
    referred_id bigint not null references users(telegram_id) on delete restrict,
    currency text not null check (currency in ('TON', 'USDT')),
    amount numeric(36, 9) not null check (amount > 0),
    created_at timestamptz not null default timezone('utc', now()),
    unique (deal_id, referrer_id, referred_id)
);

create table if not exists referral_balances (
    user_id bigint not null references users(telegram_id) on delete cascade,
    currency text not null check (currency in ('TON', 'USDT')),
    balance numeric(36, 9) not null default 0 check (balance >= 0),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (user_id, currency)
);

create table if not exists referral_withdrawals (
    id bigint generated always as identity primary key,
    user_id bigint not null references users(telegram_id) on delete restrict,
    currency text not null check (currency in ('TON', 'USDT')),
    amount numeric(36, 9) not null check (amount > 0),
    amount_atomic numeric(36, 0) not null check (amount_atomic > 0),
    destination text not null,
    comment text not null,
    status text not null default 'creating' check (
        status in ('creating', 'prepared', 'submitted', 'confirmed', 'bounced', 'failed')
    ),
    external_message_hash text,
    signed_boc text,
    valid_until timestamptz,
    submitted_at timestamptz,
    confirmed_at timestamptz,
    last_checked_at timestamptz,
    error text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);
create unique index if not exists referral_withdrawals_one_open_idx
    on referral_withdrawals(user_id, currency)
    where status in ('creating', 'prepared', 'submitted');
create index if not exists referral_withdrawals_status_idx on referral_withdrawals(status);

insert into referral_balances(user_id, currency, balance)
select referrer_id, 'TON', sum(earned_ton) from referrals group by referrer_id
on conflict (user_id, currency) do nothing;
insert into referral_balances(user_id, currency, balance)
select referrer_id, 'USDT', sum(earned_usdt) from referrals group by referrer_id
on conflict (user_id, currency) do nothing;
drop index if exists deals_unsuccessful_retention_idx;
create index deals_unsuccessful_retention_idx on deals(updated_at)
where status in (
    'cancelled', 'creation_failed', 'collection_failed',
    'payout_failed', 'payout_bounced', 'refund_failed', 'refund_bounced'
);

commit;
