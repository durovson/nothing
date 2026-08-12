begin;

alter table public.observed_deposits
    add column if not exists desk_checked_at timestamptz;

create table if not exists public.desk_listings (
    id bigint generated always as identity primary key,
    public_id text not null unique check (public_id ~ '^[A-Za-z0-9_-]{10,32}$'),
    owner_id bigint not null references public.users(telegram_id) on delete restrict,
    owner_username text not null check (owner_username ~ '^[A-Za-z0-9_]{5,32}$'),
    owner_language text not null default 'ru' check (owner_language in ('ru','en')),
    kind text not null check (kind in ('WTS','WTB')),
    description text not null check (char_length(description) between 1 and 2000),
    deal_currency text not null check (deal_currency in ('TON','USDT')),
    price numeric(36,9) check (price is null or price > 0),
    payment_currency text not null check (payment_currency in ('TON','USDT')),
    publication_fee numeric(36,9) not null check (publication_fee > 0),
    publication_fee_atomic bigint not null check (publication_fee_atomic > 0),
    status text not null default 'waiting_payment' check (
        status in ('waiting_payment','publishing','published','expired','publication_failed')
    ),
    payment_deadline_at timestamptz not null,
    observed_deposit_id bigint unique references public.observed_deposits(id) on delete restrict,
    paid_tx_hash text unique,
    paid_tx_lt bigint,
    payment_sender text,
    paid_at timestamptz,
    topic_message_id bigint,
    published_at timestamptz,
    failure_reason text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists desk_listings_payment_lookup_idx
    on public.desk_listings(lower(owner_username), payment_currency, status, payment_deadline_at);
create unique index if not exists desk_listings_one_waiting_per_owner_idx
    on public.desk_listings(owner_id)
    where status = 'waiting_payment';

alter table public.desk_listings enable row level security;
revoke all on table public.desk_listings from public, anon, authenticated;
grant select, insert, update on table public.desk_listings to service_role;
grant usage, select on sequence public.desk_listings_id_seq to service_role;

create or replace function public.create_desk_listing(
    p_public_id text,
    p_owner_id bigint,
    p_owner_username text,
    p_owner_language text,
    p_kind text,
    p_description text,
    p_deal_currency text,
    p_price numeric,
    p_payment_currency text,
    p_publication_fee numeric,
    p_publication_fee_atomic bigint,
    p_payment_deadline_at timestamptz
) returns setof public.desk_listings
language plpgsql security definer set search_path = public as $$
begin
    update public.desk_listings
       set status='expired', updated_at=timezone('utc', now())
     where owner_id=p_owner_id and status='waiting_payment';
    return query insert into public.desk_listings(
        public_id,owner_id,owner_username,owner_language,kind,description,deal_currency,price,
        payment_currency,publication_fee,publication_fee_atomic,payment_deadline_at
    ) values (
        p_public_id,p_owner_id,lower(ltrim(btrim(p_owner_username),'@')),p_owner_language,p_kind,
        p_description,p_deal_currency,p_price,p_payment_currency,p_publication_fee,
        p_publication_fee_atomic,p_payment_deadline_at
    ) returning *;
end;
$$;

create or replace function public.claim_desk_listing_payment(
    p_listing_id bigint,
    p_observed_deposit_id bigint,
    p_tx_hash text,
    p_tx_lt bigint,
    p_sender text,
    p_amount_atomic bigint
) returns setof public.desk_listings
language plpgsql security definer set search_path = public as $$
begin
    return query update public.desk_listings
       set status='publishing', observed_deposit_id=p_observed_deposit_id,
           paid_tx_hash=p_tx_hash, paid_tx_lt=p_tx_lt, payment_sender=p_sender,
           paid_at=timezone('utc', now()), updated_at=timezone('utc', now())
     where id=p_listing_id and status='waiting_payment'
       and payment_deadline_at >= timezone('utc', now())
       and publication_fee_atomic=p_amount_atomic
       and not exists (
           select 1 from public.desk_listings d
            where d.observed_deposit_id=p_observed_deposit_id or d.paid_tx_hash=p_tx_hash
       )
     returning *;
end;
$$;

create or replace function public.find_desk_listing_by_sender(
    p_sender text, p_currency text
) returns setof public.desk_listings
language sql security definer set search_path = public as $$
    select d.* from public.desk_listings d
    join public.users u on u.telegram_id=d.owner_id
    where d.status='waiting_payment'
      and d.payment_deadline_at >= timezone('utc',now())
      and d.payment_currency=p_currency
      and u.wallet_address is not null
      and btrim(u.wallet_address)=btrim(p_sender)
    order by d.id desc limit 1;
$$;

create or replace function public.mark_desk_listing_published(
    p_listing_id bigint, p_topic_message_id bigint
) returns setof public.desk_listings
language plpgsql security definer set search_path = public as $$
begin
    return query update public.desk_listings
       set status='published', topic_message_id=p_topic_message_id,
           published_at=timezone('utc', now()), failure_reason=null,
           updated_at=timezone('utc', now())
     where id=p_listing_id and status='publishing' and topic_message_id is null
     returning *;
end;
$$;

create or replace function public.expire_due_desk_listings()
returns integer language plpgsql security definer set search_path = public as $$
declare v_count integer;
begin
    update public.desk_listings set status='expired', updated_at=timezone('utc', now())
     where status='waiting_payment' and payment_deadline_at < timezone('utc', now());
    get diagnostics v_count = row_count;
    return v_count;
end;
$$;

create or replace function public.plan_desk_invalid_payment_refund(
    p_observed_deposit_id bigint, p_reason text
) returns void language plpgsql security definer set search_path = public as $$
declare
    v_deposit public.observed_deposits%rowtype;
    v_payment_id bigint;
begin
    select * into v_deposit from public.observed_deposits
     where id=p_observed_deposit_id for update;
    if not found or v_deposit.processed_at is not null then return; end if;
    if v_deposit.sender is null then
        insert into public.unmatched_payments(
            observed_deposit_id,tx_hash,tx_lt,currency,amount_atomic,sender,memo,reason
        ) values (
            v_deposit.id,v_deposit.tx_hash,v_deposit.tx_lt,v_deposit.currency,
            v_deposit.amount_atomic,null,v_deposit.memo,p_reason || ':missing_sender'
        ) on conflict (observed_deposit_id) do nothing;
        update public.observed_deposits set processed_at=timezone('utc',now()) where id=v_deposit.id;
        return;
    end if;
    insert into public.unmatched_payments(
        observed_deposit_id,tx_hash,tx_lt,currency,amount_atomic,sender,memo,reason,status,
        resolution_note
    ) values (
        v_deposit.id,v_deposit.tx_hash,v_deposit.tx_lt,v_deposit.currency,
        v_deposit.amount_atomic,v_deposit.sender,v_deposit.memo,p_reason,'refund_pending',
        'Automatic Desk refund to observed sender'
    ) on conflict (observed_deposit_id) do update set
        status='refund_pending', resolution_note='Automatic Desk refund to observed sender',
        updated_at=timezone('utc',now())
    returning id into v_payment_id;
    insert into public.financial_operations(
        idempotency_key,unmatched_payment_id,flow,type,currency,amount_atomic,
        destination,comment,metadata
    ) values (
        'desk-invalid:'||v_deposit.id||':refund',v_payment_id,'unmatched_refund',
        'buyer_refund',v_deposit.currency,v_deposit.amount_atomic,v_deposit.sender,
        'Desk payment refund',jsonb_build_object('source_tx_hash',v_deposit.tx_hash,'reason',p_reason)
    ) on conflict (idempotency_key) do nothing;
    update public.observed_deposits set processed_at=timezone('utc',now()) where id=v_deposit.id;
end;
$$;

revoke all on function public.create_desk_listing(text,bigint,text,text,text,text,text,numeric,text,numeric,bigint,timestamptz) from public,anon,authenticated;
revoke all on function public.claim_desk_listing_payment(bigint,bigint,text,bigint,text,bigint) from public,anon,authenticated;
revoke all on function public.find_desk_listing_by_sender(text,text) from public,anon,authenticated;
revoke all on function public.mark_desk_listing_published(bigint,bigint) from public,anon,authenticated;
revoke all on function public.expire_due_desk_listings() from public,anon,authenticated;
revoke all on function public.plan_desk_invalid_payment_refund(bigint,text) from public,anon,authenticated;
grant execute on function public.create_desk_listing(text,bigint,text,text,text,text,text,numeric,text,numeric,bigint,timestamptz) to service_role;
grant execute on function public.claim_desk_listing_payment(bigint,bigint,text,bigint,text,bigint) to service_role;
grant execute on function public.find_desk_listing_by_sender(text,text) to service_role;
grant execute on function public.mark_desk_listing_published(bigint,bigint) to service_role;
grant execute on function public.expire_due_desk_listings() to service_role;
grant execute on function public.plan_desk_invalid_payment_refund(bigint,text) to service_role;

commit;
