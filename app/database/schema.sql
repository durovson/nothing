create sequence if not exists deal_subwallet_id_seq
    as bigint minvalue 100000 maxvalue 4294967295 start with 100000 no cycle;

create table if not exists users (
    telegram_id bigint primary key,
    username text,
    wallet_address text,
    language text not null default 'ru',
    referrer_id bigint references users(telegram_id) on delete set null,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists deals (
    id bigint generated always as identity primary key,
    public_id text not null unique,
    subwallet_id bigint not null default nextval('deal_subwallet_id_seq') unique,
    creator_id bigint not null references users(telegram_id) on delete cascade,
    buyer_id bigint references users(telegram_id) on delete set null,
    deal_type text not null check (deal_type in ('gifts', 'channel', 'account')),
    description text not null,
    currency text not null check (currency in ('TON', 'USDT_TON')),
    amount numeric(36, 9) not null check (amount > 0),
    status text not null default 'creating',
    wallet_address text,
    paid_tx_hash text,
    paid_tx_lt numeric(20, 0),
    paid_amount_atomic numeric(30, 0),
    payment_sender text,
    paid_at timestamptz,
    failure_reason text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    check (subwallet_id between 0 and 4294967295)
);

-- Safe upgrade path for the original schema.
alter table deals add column if not exists public_id text;
alter table deals add column if not exists subwallet_id bigint;
alter table deals add column if not exists paid_tx_hash text;
alter table deals add column if not exists paid_tx_lt numeric(20, 0);
alter table deals add column if not exists paid_amount_atomic numeric(30, 0);
alter table deals add column if not exists payment_sender text;
alter table deals add column if not exists paid_at timestamptz;
alter table deals add column if not exists failure_reason text;
alter table deals add column if not exists updated_at timestamptz not null default timezone('utc', now());

update deals
set public_id = substring(md5(id::text || clock_timestamp()::text || random()::text), 1, 10)
where public_id is null;

update deals
set subwallet_id = 100000 + id
where subwallet_id is null;

select setval(
    'deal_subwallet_id_seq',
    greatest(100000, coalesce((select max(subwallet_id) + 1 from deals), 100000)),
    false
);

alter table deals alter column public_id set not null;
alter table deals alter column subwallet_id set default nextval('deal_subwallet_id_seq');
alter table deals alter column subwallet_id set not null;
create unique index if not exists deals_public_id_uidx on deals(public_id);
create unique index if not exists deals_subwallet_id_uidx on deals(subwallet_id);
create unique index if not exists deals_paid_tx_hash_uidx on deals(paid_tx_hash) where paid_tx_hash is not null;

alter table deals drop constraint if exists deals_status_check;
alter table deals add constraint deals_status_check check (
    status in (
        'creating', 'pending', 'paid', 'payout_processing', 'payout_submitted',
        'payout_failed', 'payout_bounced', 'completed', 'cancelled', 'creation_failed'
    )
);

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

create table if not exists payout_attempts (
    id bigint generated always as identity primary key,
    deal_id bigint not null references deals(id) on delete restrict,
    idempotency_key text not null unique,
    status text not null check (status in ('creating', 'prepared', 'submitted', 'confirmed', 'bounced', 'failed')),
    destination text not null,
    amount_atomic numeric(30, 0) not null check (amount_atomic > 0),
    comment text not null,
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

-- Unsuccessful deals are removed by the retention RPC. Dependent financial
-- rows must be removed in the same atomic transaction.
alter table deal_payments drop constraint if exists deal_payments_deal_id_fkey;
alter table deal_payments add constraint deal_payments_deal_id_fkey
    foreign key (deal_id) references deals(id) on delete cascade;
alter table payout_attempts drop constraint if exists payout_attempts_deal_id_fkey;
alter table payout_attempts add constraint payout_attempts_deal_id_fkey
    foreign key (deal_id) references deals(id) on delete cascade;

create table if not exists referrals (
    id bigint generated always as identity primary key,
    referrer_id bigint not null references users(telegram_id) on delete cascade,
    referred_id bigint not null references users(telegram_id) on delete cascade,
    earned_ton numeric(36, 9) not null default 0,
    earned_usdt numeric(36, 9) not null default 0,
    created_at timestamptz not null default timezone('utc', now()),
    unique (referrer_id, referred_id)
);

create index if not exists deals_status_idx on deals(status);
create index if not exists deals_creator_idx on deals(creator_id);
create index if not exists deals_buyer_idx on deals(buyer_id);
create index if not exists payout_attempts_status_idx on payout_attempts(status);
create index if not exists deals_unsuccessful_retention_idx on deals(updated_at)
where status in ('cancelled', 'creation_failed', 'payout_failed', 'payout_bounced');

create or replace function claim_deal_buyer(p_public_id text, p_buyer_id bigint)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
begin
    select * into v_deal from deals where public_id = p_public_id for update;
    if not found or v_deal.status <> 'pending' or v_deal.creator_id = p_buyer_id then
        return;
    end if;
    if v_deal.buyer_id is not null and v_deal.buyer_id <> p_buyer_id then
        return;
    end if;
    if v_deal.buyer_id is null then
        update deals set buyer_id = p_buyer_id, updated_at = timezone('utc', now())
        where id = v_deal.id returning * into v_deal;
    end if;
    return next v_deal;
end;
$$;

create or replace function assign_user_referrer(
    p_referrer_id bigint,
    p_referred_id bigint
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
    v_current_referrer bigint;
begin
    if p_referrer_id = p_referred_id then
        return false;
    end if;
    if not exists (select 1 from users where telegram_id = p_referrer_id) then
        return false;
    end if;

    select referrer_id into v_current_referrer
    from users
    where telegram_id = p_referred_id
    for update;
    if not found or v_current_referrer is not null then
        return false;
    end if;

    update users set referrer_id = p_referrer_id where telegram_id = p_referred_id;
    insert into referrals(referrer_id, referred_id)
    values (p_referrer_id, p_referred_id)
    on conflict (referrer_id, referred_id) do nothing;
    return true;
end;
$$;

create or replace function credit_referral_reward(
    p_referrer_id bigint,
    p_referred_id bigint,
    p_currency text,
    p_amount numeric
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_amount is null or p_amount <= 0 then
        raise exception 'referral reward must be positive';
    end if;
    if p_currency = 'TON' then
        insert into referrals(referrer_id, referred_id, earned_ton)
        values (p_referrer_id, p_referred_id, p_amount)
        on conflict (referrer_id, referred_id)
        do update set earned_ton = referrals.earned_ton + excluded.earned_ton;
    elsif p_currency = 'USDT_TON' then
        insert into referrals(referrer_id, referred_id, earned_usdt)
        values (p_referrer_id, p_referred_id, p_amount)
        on conflict (referrer_id, referred_id)
        do update set earned_usdt = referrals.earned_usdt + excluded.earned_usdt;
    else
        raise exception 'unsupported referral currency: %', p_currency;
    end if;
end;
$$;

create or replace function claim_deal_payment(
    p_deal_id bigint,
    p_tx_hash text,
    p_tx_lt numeric,
    p_amount_atomic numeric,
    p_sender text,
    p_observed_at timestamptz
) returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_payment_id bigint;
begin
    select * into v_deal from deals where id = p_deal_id for update;
    if not found or v_deal.status <> 'pending' then
        return;
    end if;

    insert into deal_payments(deal_id, tx_hash, tx_lt, amount_atomic, sender, observed_at)
    values (p_deal_id, p_tx_hash, p_tx_lt, p_amount_atomic, p_sender, p_observed_at)
    on conflict do nothing
    returning id into v_payment_id;
    if v_payment_id is null then
        return;
    end if;

    update deals
    set status = 'paid', paid_tx_hash = p_tx_hash, paid_tx_lt = p_tx_lt,
        paid_amount_atomic = p_amount_atomic, payment_sender = p_sender,
        paid_at = p_observed_at, updated_at = timezone('utc', now())
    where id = p_deal_id
    returning * into v_deal;
    return next v_deal;
end;
$$;

create or replace function claim_deal_payout(
    p_deal_id bigint,
    p_destination text,
    p_amount_atomic numeric,
    p_comment text
) returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_attempt payout_attempts%rowtype;
begin
    select * into v_deal from deals where id = p_deal_id for update;
    if not found or v_deal.status <> 'paid' then
        return;
    end if;
    if exists (select 1 from payout_attempts where deal_id = p_deal_id) then
        return;
    end if;

    insert into payout_attempts(
        deal_id, idempotency_key, status, destination, amount_atomic, comment
    ) values (
        p_deal_id, 'deal:' || p_deal_id::text || ':seller', 'creating',
        p_destination, p_amount_atomic, p_comment
    ) returning * into v_attempt;

    update deals
    set status = 'payout_processing', updated_at = timezone('utc', now())
    where id = p_deal_id;
    return next v_attempt;
end;
$$;

create or replace function save_prepared_payout(
    p_attempt_id bigint,
    p_external_message_hash text,
    p_signed_boc text,
    p_valid_until timestamptz
) returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
begin
    return query
    update payout_attempts
    set status = 'prepared', external_message_hash = p_external_message_hash,
        signed_boc = p_signed_boc, valid_until = p_valid_until,
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'creating'
    returning *;
end;
$$;

create or replace function mark_payout_submitted(p_attempt_id bigint)
returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'submitted', submitted_at = timezone('utc', now()),
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'prepared'
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    update deals set status = 'payout_submitted', updated_at = timezone('utc', now())
    where id = v_deal_id and status = 'payout_processing';
    return query select * from payout_attempts where id = p_attempt_id;
end;
$$;

create or replace function mark_payout_confirmed(p_attempt_id bigint)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'confirmed', confirmed_at = timezone('utc', now()),
        last_checked_at = timezone('utc', now()), updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'submitted'
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query
    update deals set status = 'completed', failure_reason = null,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status = 'payout_submitted'
    returning *;
end;
$$;

create or replace function mark_payout_bounced(p_attempt_id bigint, p_error text)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'bounced', error = p_error, last_checked_at = timezone('utc', now()),
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status in ('prepared', 'submitted')
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query
    update deals set status = 'payout_bounced', failure_reason = p_error,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status in ('payout_processing', 'payout_submitted')
    returning *;
end;
$$;

create or replace function mark_payout_failed(p_attempt_id bigint, p_error text)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'failed', error = p_error, last_checked_at = timezone('utc', now()),
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status in ('creating', 'prepared', 'submitted')
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query
    update deals set status = 'payout_failed', failure_reason = p_error,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status in ('payout_processing', 'payout_submitted')
    returning *;
end;
$$;

create or replace function purge_expired_unsuccessful_deals(p_retention_days integer)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deleted bigint;
begin
    if p_retention_days is null or p_retention_days < 1 or p_retention_days > 30 then
        raise exception 'retention must be between 1 and 30 days';
    end if;

    delete from deals
    where status in ('cancelled', 'creation_failed', 'payout_failed', 'payout_bounced')
      and updated_at < timezone('utc', now()) - make_interval(days => p_retention_days);

    get diagnostics v_deleted = row_count;
    return v_deleted;
end;
$$;

alter table users enable row level security;
alter table deals enable row level security;
alter table deal_payments enable row level security;
alter table payout_attempts enable row level security;
alter table referrals enable row level security;

revoke all on function claim_deal_payment(bigint, text, numeric, numeric, text, timestamptz) from public, anon, authenticated;
revoke all on function claim_deal_buyer(text, bigint) from public, anon, authenticated;
revoke all on function assign_user_referrer(bigint, bigint) from public, anon, authenticated;
revoke all on function credit_referral_reward(bigint, bigint, text, numeric) from public, anon, authenticated;
revoke all on function claim_deal_payout(bigint, text, numeric, text) from public, anon, authenticated;
revoke all on function save_prepared_payout(bigint, text, text, timestamptz) from public, anon, authenticated;
revoke all on function mark_payout_submitted(bigint) from public, anon, authenticated;
revoke all on function mark_payout_confirmed(bigint) from public, anon, authenticated;
revoke all on function mark_payout_bounced(bigint, text) from public, anon, authenticated;
revoke all on function mark_payout_failed(bigint, text) from public, anon, authenticated;
revoke all on function purge_expired_unsuccessful_deals(integer) from public, anon, authenticated;

grant execute on function claim_deal_payment(bigint, text, numeric, numeric, text, timestamptz) to service_role;
grant execute on function claim_deal_buyer(text, bigint) to service_role;
grant execute on function assign_user_referrer(bigint, bigint) to service_role;
grant execute on function credit_referral_reward(bigint, bigint, text, numeric) to service_role;
grant execute on function claim_deal_payout(bigint, text, numeric, text) to service_role;
grant execute on function save_prepared_payout(bigint, text, text, timestamptz) to service_role;
grant execute on function mark_payout_submitted(bigint) to service_role;
grant execute on function mark_payout_confirmed(bigint) to service_role;
grant execute on function mark_payout_bounced(bigint, text) to service_role;
grant execute on function mark_payout_failed(bigint, text) to service_role;
grant execute on function purge_expired_unsuccessful_deals(integer) to service_role;
