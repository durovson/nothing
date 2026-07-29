begin;

create extension if not exists pgcrypto;

alter table public.deals add column if not exists archived_at timestamptz;
alter table public.deals add column if not exists archived_reason text;
alter table public.deals add column if not exists buyer_wallet_snapshot text;
update public.deals set buyer_wallet_snapshot=buyer_wallet_address
  where buyer_wallet_snapshot is null and buyer_wallet_address is not null;

create table if not exists public.financial_operations (
    id bigint generated always as identity primary key,
    operation_id uuid not null default gen_random_uuid() unique,
    idempotency_key text not null unique,
    deal_id bigint references public.deals(id) on delete restrict,
    referral_withdrawal_id bigint references public.referral_withdrawals(id) on delete restrict,
    unmatched_payment_id bigint,
    flow text not null check (flow in ('collection','payout','refund','referral','unmatched_refund')),
    type text not null check (type in (
        'collection_transfer','seller_transfer','buyer_refund','service_fee_transfer','referral_transfer'
    )),
    status text not null default 'pending' check (status in (
        'pending','prepared','submitted','confirmed','failed','bounced','manual_review'
    )),
    currency text not null check (currency in ('TON','USDT')),
    amount_atomic numeric(36, 0) not null check (amount_atomic > 0),
    destination text not null check (char_length(btrim(destination)) between 40 and 128),
    comment text not null check (char_length(btrim(comment)) between 1 and 120),
    tx_hash text,
    retry_count integer not null default 0 check (retry_count >= 0),
    last_error text check (last_error is null or char_length(last_error) <= 1000),
    next_retry_at timestamptz not null default timezone('utc', now()),
    locked_until timestamptz,
    submitted_at timestamptz,
    completed_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists financial_operations_due_idx
    on public.financial_operations(flow, next_retry_at, id)
    where status in ('pending','failed','bounced');
create index if not exists financial_operations_submitted_idx
    on public.financial_operations(flow, id) where status = 'submitted';
create index if not exists financial_operations_deal_idx
    on public.financial_operations(deal_id, flow, id) where deal_id is not null;

create table if not exists public.financial_dispatch_lock (
    id smallint primary key check(id=1),
    operation_id bigint references public.financial_operations(id) on delete restrict,
    locked_until timestamptz,
    updated_at timestamptz not null default timezone('utc',now())
);
insert into public.financial_dispatch_lock(id) values(1) on conflict(id) do nothing;

create table if not exists public.financial_operation_attempts (
    id bigint generated always as identity primary key,
    operation_id bigint not null references public.financial_operations(id) on delete restrict,
    attempt_no integer not null check (attempt_no > 0),
    status text not null check (status in (
        'prepared','submitted','confirmed','failed','bounced','unknown'
    )),
    external_message_hash text not null unique,
    signed_boc text not null,
    valid_until timestamptz not null,
    tx_hash text,
    submitted_at timestamptz,
    completed_at timestamptz,
    last_checked_at timestamptz,
    error text check (error is null or char_length(error) <= 1000),
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    unique (operation_id, attempt_no)
);
create index if not exists financial_operation_attempts_open_idx
    on public.financial_operation_attempts(operation_id, id)
    where status in ('prepared','submitted','unknown');

create table if not exists public.deposit_scanner_cursors (
    scanner text primary key,
    account_address text not null,
    last_lt numeric(20, 0),
    last_hash text,
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.observed_deposits (
    id bigint generated always as identity primary key,
    tx_hash text not null unique,
    tx_lt numeric(20, 0) not null,
    currency text not null check (currency in ('TON','USDT')),
    amount_atomic numeric(36, 0) not null check (amount_atomic > 0),
    sender text,
    memo text,
    account_address text not null,
    jetton_master_address text,
    jetton_wallet_address text,
    observed_at timestamptz not null,
    matched_deal_id bigint references public.deals(id) on delete restrict,
    processed_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    unique (account_address, tx_lt)
);
alter table public.observed_deposits add column if not exists jetton_master_address text;
alter table public.observed_deposits add column if not exists jetton_wallet_address text;

create table if not exists public.unmatched_payments (
    id bigint generated always as identity primary key,
    observed_deposit_id bigint not null unique
        references public.observed_deposits(id) on delete restrict,
    tx_hash text not null unique,
    tx_lt numeric(20, 0) not null,
    currency text not null check (currency in ('TON','USDT')),
    amount_atomic numeric(36, 0) not null check (amount_atomic > 0),
    sender text,
    memo text,
    reason text not null check (char_length(btrim(reason)) between 3 and 1000),
    status text not null default 'open' check (status in (
        'open','refund_pending','refunded','linked','ignored'
    )),
    resolution_note text,
    resolved_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);
alter table public.financial_operations drop constraint if exists financial_operations_unmatched_payment_id_fkey;
alter table public.financial_operations add constraint financial_operations_unmatched_payment_id_fkey
    foreign key (unmatched_payment_id) references public.unmatched_payments(id) on delete restrict;
create index if not exists unmatched_payments_open_idx
    on public.unmatched_payments(created_at, id) where status = 'open';

-- Financial evidence is immutable with respect to deal deletion.
alter table public.deal_payments drop constraint if exists deal_payments_deal_id_fkey;
alter table public.deal_payments add constraint deal_payments_deal_id_fkey
    foreign key (deal_id) references public.deals(id) on delete restrict;
alter table public.collection_attempts drop constraint if exists collection_attempts_deal_id_fkey;
alter table public.collection_attempts add constraint collection_attempts_deal_id_fkey
    foreign key (deal_id) references public.deals(id) on delete restrict;
alter table public.payout_attempts drop constraint if exists payout_attempts_deal_id_fkey;
alter table public.payout_attempts add constraint payout_attempts_deal_id_fkey
    foreign key (deal_id) references public.deals(id) on delete restrict;
alter table public.refund_attempts drop constraint if exists refund_attempts_deal_id_fkey;
alter table public.refund_attempts add constraint refund_attempts_deal_id_fkey
    foreign key (deal_id) references public.deals(id) on delete restrict;
alter table public.dispute_tickets drop constraint if exists dispute_tickets_deal_id_fkey;
alter table public.dispute_tickets add constraint dispute_tickets_deal_id_fkey
    foreign key (deal_id) references public.deals(id) on delete restrict;

-- Old batch attempts are evidence, not automatically replayable operations.
insert into public.financial_operations(
  idempotency_key,deal_id,flow,type,status,currency,amount_atomic,destination,
  comment,last_error,next_retry_at,metadata
)
select 'legacy-payout-attempt:'||p.id,p.deal_id,'payout','seller_transfer','manual_review',
  p.currency,p.amount_atomic,p.destination,p.comment,
  coalesce(p.error,'Legacy batch requires per-output on-chain reconciliation'),
  'infinity'::timestamptz,
  jsonb_build_object('legacy_batch',true,'legacy_table','payout_attempts','legacy_id',p.id,
    'external_message_hash',p.external_message_hash,'reward_destination',p.reward_destination,
    'reward_amount_atomic',p.reward_nominal_amount_atomic)
from public.payout_attempts p where p.status<>'confirmed'
on conflict (idempotency_key) do nothing;

insert into public.financial_operations(
  idempotency_key,deal_id,flow,type,status,currency,amount_atomic,destination,
  comment,last_error,next_retry_at,metadata
)
select 'deal:'||c.deal_id||':collection',c.deal_id,'collection','collection_transfer',
  case when c.status='creating' and c.signed_boc is null then 'pending' else 'manual_review' end,
  'TON',greatest(coalesce(d.paid_amount_atomic,1),1),c.destination,c.comment,
  case when c.status='creating' and c.signed_boc is null then null
       else coalesce(c.error,'Legacy collection requires on-chain reconciliation') end,
  case when c.status='creating' and c.signed_boc is null then timezone('utc',now())
       else 'infinity'::timestamptz end,
  jsonb_build_object('purpose','deal_custody','source_account',d.wallet_address,
    'wallet_version',d.wallet_version,'subwallet_id',d.subwallet_id,
    'sweep_balance',true,'legacy_table','collection_attempts','legacy_id',c.id)
from public.collection_attempts c join public.deals d on d.id=c.deal_id
where c.status<>'confirmed'
on conflict(idempotency_key) do nothing;

insert into public.financial_operation_attempts(
  operation_id,attempt_no,status,external_message_hash,signed_boc,valid_until,
  submitted_at,last_checked_at,error
)
select o.id,1,'unknown',c.external_message_hash,c.signed_boc,
  coalesce(c.valid_until,timezone('utc',now())),c.submitted_at,c.last_checked_at,
  coalesce(c.error,'Imported legacy collection attempt')
from public.collection_attempts c
join public.financial_operations o on o.idempotency_key='deal:'||c.deal_id||':collection'
where c.status<>'confirmed' and c.external_message_hash is not null and c.signed_boc is not null
on conflict(external_message_hash) do nothing;

insert into public.financial_operations(
  idempotency_key,deal_id,flow,type,status,currency,amount_atomic,destination,
  comment,last_error,next_retry_at,metadata
)
select 'legacy-refund-attempt:'||r.id,r.deal_id,'refund','buyer_refund','manual_review',
  r.currency,r.amount_atomic,r.destination,r.comment,
  coalesce(r.error,'Legacy batch requires per-output on-chain reconciliation'),
  'infinity'::timestamptz,
  jsonb_build_object('legacy_batch',true,'legacy_table','refund_attempts','legacy_id',r.id,
    'external_message_hash',r.external_message_hash,'reward_destination',r.reward_destination,
    'reward_amount_atomic',r.reward_nominal_amount_atomic)
from public.refund_attempts r where r.status<>'confirmed'
on conflict (idempotency_key) do nothing;

create or replace function public.financial_retry_delay(p_retry_count integer)
returns interval language sql immutable as $$
    select case greatest(p_retry_count, 1)
        when 1 then interval '1 minute'
        when 2 then interval '5 minutes'
        when 3 then interval '15 minutes'
        when 4 then interval '1 hour'
        when 5 then interval '6 hours'
        else interval '24 hours'
    end;
$$;

create or replace function public.plan_deal_collection_operation(
    p_deal_id bigint,
    p_destination text,
    p_comment text,
    p_unmatched_payment_id bigint default null
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare
    v_deal public.deals%rowtype;
    v_unmatched public.unmatched_payments%rowtype;
    v_source_account text;
    v_amount numeric;
    v_key text;
    v_purpose text;
    v_existing_id bigint;
begin
    select * into v_deal from public.deals where id=p_deal_id for update;
    if not found or v_deal.currency<>'TON' or v_deal.wallet_address is null then return; end if;

    if p_unmatched_payment_id is null then
      if v_deal.status not in ('collecting','collection_submitted') then return; end if;
      select id into v_existing_id from public.financial_operations
        where flow='collection' and status<>'confirmed'
          and metadata->>'source_account'=v_deal.wallet_address
        order by id for update limit 1;
      if v_existing_id is not null then
        return query update public.financial_operations
          set metadata=jsonb_set(metadata,'{purpose}','"deal_custody"'::jsonb),
            deal_id=p_deal_id,updated_at=timezone('utc',now())
          where id=v_existing_id returning *;
        return;
      end if;
      v_amount:=v_deal.paid_amount_atomic;
      v_key:='deal:'||p_deal_id||':collection';
      v_purpose:='deal_custody';
    else
      select u.* into v_unmatched
      from public.unmatched_payments u
      join public.observed_deposits o on o.id=u.observed_deposit_id
      where u.id=p_unmatched_payment_id and u.status='open'
        and o.account_address=v_deal.wallet_address for update of u;
      if not found then return; end if;
      v_amount:=v_unmatched.amount_atomic;
      v_key:='unmatched-payment:'||p_unmatched_payment_id||':collection';
      v_purpose:='unmatched_recovery';
    end if;
    if coalesce(v_amount,0)<=0 then raise exception 'collection amount is not positive'; end if;
    v_source_account:=v_deal.wallet_address;

    return query insert into public.financial_operations(
      idempotency_key,deal_id,unmatched_payment_id,flow,type,currency,amount_atomic,
      destination,comment,metadata
    ) values (
      v_key,p_deal_id,p_unmatched_payment_id,'collection','collection_transfer','TON',v_amount,
      p_destination,p_comment,jsonb_build_object(
        'purpose',v_purpose,'source_account',v_source_account,
        'wallet_version',v_deal.wallet_version,'subwallet_id',v_deal.subwallet_id,
        'sweep_balance',true
      )
    ) on conflict (idempotency_key) do update set updated_at=excluded.updated_at
      returning *;
end;
$$;

create or replace function public.plan_deal_payout_operations(
    p_deal_id bigint,
    p_seller_destination text,
    p_seller_amount_atomic numeric,
    p_seller_comment text,
    p_service_destination text,
    p_service_amount_atomic numeric,
    p_service_comment text,
    p_referral_allocations jsonb default '[]'::jsonb
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_deal public.deals%rowtype;
begin
    select * into v_deal from public.deals where id = p_deal_id for update;
    if not found or v_deal.status not in ('release_requested','payout_processing') then return; end if;
    if p_seller_amount_atomic <= 0 or p_service_amount_atomic < 0 then
        raise exception 'invalid payout amounts';
    end if;

    insert into public.financial_operations(
        idempotency_key, deal_id, flow, type, currency, amount_atomic,
        destination, comment, metadata
    ) values (
        'deal:' || p_deal_id || ':payout:seller', p_deal_id, 'payout',
        'seller_transfer', v_deal.currency, p_seller_amount_atomic,
        p_seller_destination, p_seller_comment,
        jsonb_build_object('referral_allocations',coalesce(p_referral_allocations,'[]'::jsonb))
    ) on conflict (idempotency_key) do nothing;

    if p_service_amount_atomic > 0 then
        insert into public.financial_operations(
            idempotency_key, deal_id, flow, type, currency, amount_atomic,
            destination, comment
        ) values (
            'deal:' || p_deal_id || ':payout:service', p_deal_id, 'payout',
            'service_fee_transfer', v_deal.currency, p_service_amount_atomic,
            p_service_destination, p_service_comment
        ) on conflict (idempotency_key) do nothing;
    end if;

    update public.deals set status = 'payout_processing', updated_at = timezone('utc', now())
    where id = p_deal_id and status = 'release_requested';
    return query select * from public.financial_operations
        where deal_id = p_deal_id and flow = 'payout' order by id;
end;
$$;

create or replace function public.plan_deal_refund_operations(
    p_deal_id bigint,
    p_buyer_destination text,
    p_buyer_amount_atomic numeric,
    p_buyer_comment text,
    p_service_destination text,
    p_service_amount_atomic numeric,
    p_service_comment text
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_deal public.deals%rowtype;
begin
    select * into v_deal from public.deals where id = p_deal_id for update;
    if not found or v_deal.status not in ('refund_requested','refund_processing') then return; end if;
    if p_buyer_amount_atomic <= 0 or p_service_amount_atomic < 0 then
        raise exception 'invalid refund amounts';
    end if;

    insert into public.financial_operations(
        idempotency_key, deal_id, flow, type, currency, amount_atomic,
        destination, comment
    ) values (
        'deal:' || p_deal_id || ':refund:buyer', p_deal_id, 'refund',
        'buyer_refund', v_deal.currency, p_buyer_amount_atomic,
        p_buyer_destination, p_buyer_comment
    ) on conflict (idempotency_key) do nothing;

    if p_service_amount_atomic > 0 then
        insert into public.financial_operations(
            idempotency_key, deal_id, flow, type, currency, amount_atomic,
            destination, comment
        ) values (
            'deal:' || p_deal_id || ':refund:service', p_deal_id, 'refund',
            'service_fee_transfer', v_deal.currency, p_service_amount_atomic,
            p_service_destination, p_service_comment
        ) on conflict (idempotency_key) do nothing;
    end if;

    update public.deals set status = 'refund_processing', updated_at = timezone('utc', now())
    where id = p_deal_id and status = 'refund_requested';
    return query select * from public.financial_operations
        where deal_id = p_deal_id and flow = 'refund' order by id;
end;
$$;

create or replace function public.claim_referral_withdrawal_operation(
    p_user_id bigint, p_currency text, p_destination text, p_comment text
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare
    v_balance public.referral_balances%rowtype;
    v_withdrawal public.referral_withdrawals%rowtype;
    v_atomic numeric;
begin
    if p_currency not in ('TON','USDT') then raise exception 'unsupported currency'; end if;
    select * into v_balance from public.referral_balances
      where user_id = p_user_id and currency = p_currency for update;
    if not found or v_balance.balance <= 0 then return; end if;
    if exists (
        select 1 from public.financial_operations
        where flow = 'referral' and metadata->>'user_id' = p_user_id::text
          and currency = p_currency and status <> 'confirmed'
    ) then return; end if;
    v_atomic := trunc(v_balance.balance * case when p_currency='TON' then 1000000000 else 1000000 end);
    if v_atomic <= 0 then return; end if;

    update public.referral_balances set balance=0, updated_at=timezone('utc', now())
      where user_id=p_user_id and currency=p_currency;
    insert into public.referral_withdrawals(
        user_id,currency,amount,amount_atomic,destination,comment,status
    ) values (
        p_user_id,p_currency,v_balance.balance,v_atomic,p_destination,p_comment,'creating'
    ) returning * into v_withdrawal;
    return query insert into public.financial_operations(
        idempotency_key,referral_withdrawal_id,flow,type,currency,amount_atomic,
        destination,comment,metadata
    ) values (
        'referral-withdrawal:' || v_withdrawal.id, v_withdrawal.id, 'referral',
        'referral_transfer',p_currency,v_atomic,p_destination,p_comment,
        jsonb_build_object('user_id',p_user_id,'amount',v_balance.balance)
    ) returning *;
end;
$$;

create or replace function public.plan_unmatched_refund_operation(
    p_payment_id bigint,
    p_destination text,
    p_comment text default 'Недействительный платеж'
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_payment public.unmatched_payments%rowtype;
begin
    select * into v_payment from public.unmatched_payments
      where id=p_payment_id for update;
    if not found or v_payment.status not in ('open','refund_pending') then return; end if;
    if v_payment.sender is null or btrim(p_destination) is distinct from btrim(v_payment.sender) then
      raise exception 'unmatched payment can only be returned to its observed sender';
    end if;
    if btrim(p_comment) <> 'Недействительный платеж' then
      raise exception 'invalid unmatched refund comment';
    end if;
    if v_payment.currency='TON' and not exists (
      select 1 from public.financial_operations c
      join public.observed_deposits o on o.id=v_payment.observed_deposit_id
      where c.flow='collection' and c.status='confirmed'
        and c.metadata->>'source_account'=o.account_address
    ) then
      raise exception 'TON unmatched payment has not been collected to guarant custody';
    end if;
    update public.unmatched_payments set status='refund_pending',
      resolution_note='Refund to the observed sender',updated_at=timezone('utc', now())
      where id=p_payment_id;
    return query insert into public.financial_operations(
      idempotency_key,unmatched_payment_id,flow,type,currency,amount_atomic,
      destination,comment,metadata
    ) values (
      'unmatched-payment:'||p_payment_id||':refund',p_payment_id,'unmatched_refund',
      'buyer_refund',v_payment.currency,v_payment.amount_atomic,p_destination,p_comment,
      jsonb_build_object('source_tx_hash',v_payment.tx_hash,'reason',v_payment.reason)
    ) on conflict (idempotency_key) do update set updated_at=excluded.updated_at
      returning *;
end;
$$;

create or replace function public.claim_due_financial_operation(
    p_flow text, p_lock_seconds integer default 120
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_id bigint; v_dispatch public.financial_dispatch_lock%rowtype;
begin
    select * into v_dispatch from public.financial_dispatch_lock where id=1 for update;
    if v_dispatch.locked_until is not null
       and v_dispatch.locked_until>timezone('utc',now()) then return; end if;
    if exists (
        select 1 from public.financial_operations
        where status in ('prepared','submitted')
    ) then return; end if;
    select id into v_id from public.financial_operations
    where flow = p_flow
      and status in ('pending','failed','bounced')
      and next_retry_at <= timezone('utc', now())
      and (locked_until is null or locked_until <= timezone('utc', now()))
    order by next_retry_at, id
    for update skip locked limit 1;
    if v_id is null then return; end if;
    update public.financial_dispatch_lock set operation_id=v_id,
      locked_until=timezone('utc',now())+make_interval(secs=>greatest(p_lock_seconds,30)),
      updated_at=timezone('utc',now()) where id=1;
    return query update public.financial_operations
      set locked_until=timezone('utc', now()) + make_interval(secs => greatest(p_lock_seconds,30)),
          updated_at=timezone('utc', now())
      where id=v_id returning *;
end;
$$;

create or replace function public.schedule_unprepared_financial_operation_retry(
    p_operation_id bigint, p_error text
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_retry integer;
begin
    select retry_count+1 into v_retry from public.financial_operations
      where id=p_operation_id and status in ('pending','failed','bounced') for update;
    if v_retry is null then return; end if;
    update public.financial_operations set
      status=case when v_retry>=7 then 'manual_review' else 'failed' end,
      retry_count=v_retry,last_error=left(p_error,1000),
      next_retry_at=case when v_retry>=7 then 'infinity'::timestamptz
        else timezone('utc', now())+public.financial_retry_delay(v_retry) end,
      locked_until=null,updated_at=timezone('utc', now()) where id=p_operation_id;
    update public.financial_dispatch_lock set operation_id=null,locked_until=null,
      updated_at=timezone('utc',now()) where id=1 and operation_id=p_operation_id;
    return query select * from public.financial_operations where id=p_operation_id;
end;
$$;

create or replace function public.prepare_financial_operation_attempt(
    p_operation_id bigint, p_external_message_hash text, p_signed_boc text,
    p_valid_until timestamptz
) returns setof public.financial_operation_attempts
language plpgsql security definer set search_path = public as $$
declare v_operation public.financial_operations%rowtype; v_attempt_no integer;
begin
    select * into v_operation from public.financial_operations
      where id=p_operation_id for update;
    if not found or v_operation.status not in ('pending','failed','bounced') then return; end if;
    if exists (select 1 from public.financial_operation_attempts
               where operation_id=p_operation_id and status in ('prepared','submitted','unknown')) then return; end if;
    select coalesce(max(attempt_no),0)+1 into v_attempt_no
      from public.financial_operation_attempts where operation_id=p_operation_id;
    update public.financial_operations set status='prepared', locked_until=null,
      updated_at=timezone('utc', now()) where id=p_operation_id;
    return query insert into public.financial_operation_attempts(
        operation_id,attempt_no,status,external_message_hash,signed_boc,valid_until
    ) values (
        p_operation_id,v_attempt_no,'prepared',p_external_message_hash,p_signed_boc,p_valid_until
    ) returning *;
end;
$$;

create or replace function public.mark_financial_attempt_submitted(p_attempt_id bigint)
returns setof public.financial_operation_attempts
language plpgsql security definer set search_path = public as $$
declare v_operation_id bigint;
begin
    update public.financial_operation_attempts set status='submitted',
      submitted_at=coalesce(submitted_at,timezone('utc', now())),
      last_checked_at=timezone('utc', now()),updated_at=timezone('utc', now())
      where id=p_attempt_id and status in ('prepared','submitted')
      returning operation_id into v_operation_id;
    if v_operation_id is null then return; end if;
    update public.financial_operations set status='submitted',
      submitted_at=coalesce(submitted_at,timezone('utc', now())),locked_until=null,
      updated_at=timezone('utc', now()) where id=v_operation_id;
    update public.deals d set status='collection_submitted',updated_at=timezone('utc',now())
      from public.financial_operations o
      where o.id=v_operation_id and o.flow='collection' and d.id=o.deal_id
        and d.status='collecting';
    return query select * from public.financial_operation_attempts where id=p_attempt_id;
end;
$$;

create or replace function public.finalize_financial_flow(p_operation_id bigint)
returns void language plpgsql security definer set search_path = public as $$
declare
    v_operation public.financial_operations%rowtype;
    v_meta jsonb;
    v_seller_tx text;
    v_allocation record;
begin
    select * into v_operation from public.financial_operations where id=p_operation_id;
    if not found then return; end if;
    if v_operation.deal_id is not null and exists (
        select 1 from public.financial_operations
        where deal_id=v_operation.deal_id and flow=v_operation.flow and status <> 'confirmed'
    ) then return; end if;

    if v_operation.flow='collection' then
        if v_operation.metadata->>'purpose'='deal_custody' then
          update public.deals d set
            status=case
              when exists(select 1 from public.dispute_tickets t
                where t.deal_id=d.id and t.status='open') then 'disputed'
              when d.resolution='refund' and coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address) is null
                then 'refund_awaiting_wallet'
              when d.resolution='refund' then 'refund_requested'
              else 'delivery_pending' end,
            buyer_wallet_snapshot=coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address),
            buyer_wallet_address=coalesce(d.buyer_wallet_address,d.buyer_wallet_snapshot,u.wallet_address),
            custody_confirmed_at=timezone('utc',now()),
            delivery_deadline_at=timezone('utc',now())+interval '1 hour',
            failure_reason=null,updated_at=timezone('utc',now())
          from public.users u
          where d.id=v_operation.deal_id and d.buyer_id=u.telegram_id
            and d.status in ('collecting','collection_submitted','collection_failed','disputed');
        end if;
    elsif v_operation.flow='payout' then
        select metadata,tx_hash into v_meta,v_seller_tx from public.financial_operations
          where deal_id=v_operation.deal_id and flow='payout' and type='seller_transfer' limit 1;
        for v_allocation in
          select * from jsonb_to_recordset(coalesce(v_meta->'referral_allocations','[]'::jsonb))
          as x(referrer_id bigint,referred_id bigint,amount numeric)
        loop
          if v_allocation.referrer_id is not null and v_allocation.referred_id is not null
             and coalesce(v_allocation.amount,0)>0 then
            insert into public.referral_rewards(deal_id,referrer_id,referred_id,currency,amount)
            values(v_operation.deal_id,v_allocation.referrer_id,v_allocation.referred_id,
                   v_operation.currency,v_allocation.amount)
            on conflict (deal_id,referrer_id,referred_id) do nothing;
            if found then
                insert into public.referral_balances(user_id,currency,balance)
                values(v_allocation.referrer_id,v_operation.currency,v_allocation.amount)
                on conflict (user_id,currency) do update set
                  balance=public.referral_balances.balance+excluded.balance,
                  updated_at=timezone('utc', now());
            end if;
          end if;
        end loop;
        update public.deals set status='completed',resolution=coalesce(resolution,'release'),
          payout_tx_hash=v_seller_tx,failure_reason=null,updated_at=timezone('utc', now())
          where id=v_operation.deal_id and status in ('payout_processing','payout_submitted');
    elsif v_operation.flow='refund' then
        update public.deals set status='refunded',resolution='refund',failure_reason=null,
          updated_at=timezone('utc', now())
          where id=v_operation.deal_id and status in ('refund_processing','refund_submitted');
    elsif v_operation.flow='referral' then
        update public.referral_withdrawals set status='confirmed',confirmed_at=timezone('utc', now()),
          updated_at=timezone('utc', now()) where id=v_operation.referral_withdrawal_id;
    elsif v_operation.flow='unmatched_refund' then
        update public.unmatched_payments set status='refunded',resolved_at=timezone('utc', now()),
          updated_at=timezone('utc', now()) where id=v_operation.unmatched_payment_id;
    end if;
end;
$$;

create or replace function public.mark_financial_operation_confirmed(
    p_attempt_id bigint, p_transaction_hash text
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_operation_id bigint;
begin
    update public.financial_operation_attempts set status='confirmed',tx_hash=p_transaction_hash,
      completed_at=timezone('utc', now()),last_checked_at=timezone('utc', now()),
      updated_at=timezone('utc', now())
      where id=p_attempt_id and status in ('submitted','unknown')
      returning operation_id into v_operation_id;
    if v_operation_id is null then return; end if;
    update public.financial_operations set status='confirmed',tx_hash=p_transaction_hash,
      completed_at=timezone('utc', now()),last_error=null,next_retry_at=timezone('utc', now()),
      locked_until=null,updated_at=timezone('utc', now()) where id=v_operation_id;
    update public.financial_dispatch_lock set operation_id=null,locked_until=null,
      updated_at=timezone('utc',now()) where id=1 and operation_id=v_operation_id;
    perform public.finalize_financial_flow(v_operation_id);
    return query select * from public.financial_operations where id=v_operation_id;
end;
$$;

create or replace function public.schedule_financial_operation_retry(
    p_attempt_id bigint, p_error text, p_bounced boolean default false,
    p_uncertain boolean default false
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
declare v_operation_id bigint; v_retry integer;
begin
    update public.financial_operation_attempts set
      status=case when p_uncertain then 'unknown' when p_bounced then 'bounced' else 'failed' end,
      error=left(p_error,1000),completed_at=case when p_uncertain then null else timezone('utc', now()) end,
      last_checked_at=timezone('utc', now()),updated_at=timezone('utc', now())
      where id=p_attempt_id and status in ('prepared','submitted','unknown')
      returning operation_id into v_operation_id;
    if v_operation_id is null then return; end if;
    select retry_count+1 into v_retry from public.financial_operations
      where id=v_operation_id for update;
    update public.financial_operations set
      status=case when p_uncertain or v_retry>=7 then 'manual_review'
                  when p_bounced then 'bounced' else 'failed' end,
      retry_count=v_retry,last_error=left(p_error,1000),
      next_retry_at=case when p_uncertain or v_retry>=7 then 'infinity'::timestamptz
                         else timezone('utc', now())+public.financial_retry_delay(v_retry) end,
      locked_until=null,updated_at=timezone('utc', now()) where id=v_operation_id;
    update public.financial_dispatch_lock set operation_id=null,locked_until=null,
      updated_at=timezone('utc',now()) where id=1 and operation_id=v_operation_id;
    return query select * from public.financial_operations where id=v_operation_id;
end;
$$;

create or replace function public.reopen_financial_operation(p_operation_id bigint, p_reason text)
returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
begin
    return query update public.financial_operations set status='pending',
      next_retry_at=timezone('utc', now()),locked_until=null,
      last_error=left('Reopened: '||p_reason,1000),updated_at=timezone('utc', now())
      where id=p_operation_id and status in ('manual_review','failed','bounced')
        and not exists(
          select 1 from public.financial_operation_attempts a
          where a.operation_id=p_operation_id and a.status in ('prepared','submitted','unknown')
        ) returning *;
end;
$$;

create or replace function public.mark_financial_operation_manual_review(
    p_operation_id bigint, p_reason text
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
begin
    return query update public.financial_operations set status='manual_review',
      next_retry_at='infinity'::timestamptz,locked_until=null,last_error=left(p_reason,1000),
      updated_at=timezone('utc', now()) where id=p_operation_id
        and status in ('manual_review','failed','bounced') returning *;
end;
$$;

create or replace function public.force_complete_financial_operation(
    p_operation_id bigint, p_transaction_hash text, p_reason text
) returns setof public.financial_operations
language plpgsql security definer set search_path = public as $$
begin
    update public.financial_operations set status='confirmed',tx_hash=p_transaction_hash,
      completed_at=timezone('utc', now()),last_error=left('Force completed: '||p_reason,1000),
      next_retry_at=timezone('utc', now()),locked_until=null,updated_at=timezone('utc', now())
      where id=p_operation_id and status in ('manual_review','failed','bounced');
    if not found then return; end if;
    update public.financial_dispatch_lock set operation_id=null,locked_until=null,
      updated_at=timezone('utc',now()) where id=1 and operation_id=p_operation_id;
    update public.financial_operation_attempts set status='confirmed',tx_hash=p_transaction_hash,
      completed_at=timezone('utc',now()),last_checked_at=timezone('utc',now()),
      error=left('Force completed: '||p_reason,1000),updated_at=timezone('utc',now())
      where operation_id=p_operation_id and status in ('prepared','submitted','unknown');
    perform public.finalize_financial_flow(p_operation_id);
    return query select * from public.financial_operations where id=p_operation_id;
end;
$$;

create or replace function public.archive_expired_unsuccessful_deals(p_retention_days integer)
returns bigint language plpgsql security definer set search_path = public as $$
declare v_count bigint;
begin
    if p_retention_days is null or p_retention_days<1 or p_retention_days>30 then
      raise exception 'retention must be between 1 and 30 days'; end if;
    update public.deals d set archived_at=timezone('utc', now()),
      archived_reason='Unpaid unsuccessful deal retention',updated_at=timezone('utc', now())
    where d.status in ('cancelled','creation_failed') and d.archived_at is null
      and d.paid_tx_hash is null
      and not exists(select 1 from public.deal_payments p where p.deal_id=d.id)
      and d.updated_at < timezone('utc', now())-make_interval(days=>p_retention_days);
    get diagnostics v_count=row_count;
    return v_count;
end;
$$;

create or replace function public.purge_expired_unsuccessful_deals(p_retention_days integer)
returns bigint language sql security definer set search_path = public as $$
    select public.archive_expired_unsuccessful_deals(p_retention_days);
$$;

-- After custody, cancellation is a dispute and never a direct refund.
create or replace function public.claim_deal_buyer(p_public_id text,p_buyer_id bigint)
returns setof public.deals language plpgsql security definer set search_path=public as $$
declare v_deal public.deals%rowtype; v_wallet text;
begin
  select * into v_deal from public.deals where public_id=p_public_id for update;
  if not found or v_deal.status<>'pending' or v_deal.creator_id=p_buyer_id then return; end if;
  if v_deal.buyer_id is not null and v_deal.buyer_id<>p_buyer_id then return; end if;
  select wallet_address into v_wallet from public.users where telegram_id=p_buyer_id;
  if v_wallet is null then return; end if;
  if v_deal.buyer_id is null then
    update public.deals set buyer_id=p_buyer_id,buyer_wallet_address=v_wallet,
      buyer_wallet_snapshot=v_wallet,updated_at=timezone('utc',now())
      where id=v_deal.id returning * into v_deal;
  end if;
  return next v_deal;
end;
$$;

create or replace function public.request_deal_cancellation(p_deal_id bigint,p_actor_id bigint)
returns setof public.deals language plpgsql security definer set search_path = public as $$
declare v_deal public.deals%rowtype; v_ticket_id bigint;
begin
    select * into v_deal from public.deals where id=p_deal_id for update;
    if not found or (p_actor_id<>v_deal.creator_id and p_actor_id is distinct from v_deal.buyer_id) then return; end if;
    if v_deal.status='pending' then
      update public.deals set status='cancelled',resolution='cancel',
        resolution_reason='Cancelled before payment',cancellation_requested_at=timezone('utc', now()),
        updated_at=timezone('utc', now()) where id=p_deal_id returning * into v_deal;
    elsif v_deal.status in ('collecting','collection_submitted') then
      insert into public.dispute_tickets(deal_id,opened_by,description)
      values(p_deal_id,p_actor_id,'Cancellation requested after payment confirmation')
      on conflict (deal_id) where status='open' do nothing returning id into v_ticket_id;
      if v_ticket_id is null then return; end if;
      update public.deals set resolution=null,
        resolution_reason='Payment received; cancellation requires administrator review',
        cancellation_requested_at=timezone('utc', now()),updated_at=timezone('utc', now())
        where id=p_deal_id returning * into v_deal;
    elsif v_deal.status in ('delivery_pending','delivered') then
      insert into public.dispute_tickets(deal_id,opened_by,description)
      values(p_deal_id,p_actor_id,'Cancellation requested after escrow custody confirmation')
      on conflict (deal_id) where status='open' do nothing returning id into v_ticket_id;
      if v_ticket_id is null then return; end if;
      update public.deals set status='disputed',resolution=null,
        resolution_reason='Cancellation requires administrator review',
        cancellation_requested_at=timezone('utc', now()),updated_at=timezone('utc', now())
        where id=p_deal_id returning * into v_deal;
    else return;
    end if;
    return next v_deal;
end;
$$;

create or replace function public.request_expired_delivery_refund(p_deal_id bigint)
returns setof public.deals language plpgsql security definer set search_path = public as $$
begin
    return query update public.deals d set status=case
        when coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address) is null then 'refund_awaiting_wallet'
        else 'refund_requested' end,
      buyer_wallet_snapshot=coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address),
      buyer_wallet_address=coalesce(d.buyer_wallet_address,d.buyer_wallet_snapshot,u.wallet_address),
      resolution='refund',resolution_reason='Seller delivery deadline expired',updated_at=timezone('utc', now())
    from public.users u where d.id=p_deal_id and d.buyer_id=u.telegram_id
      and d.status='delivery_pending' and d.deal_type<>'channel'
      and d.delivery_deadline_at<=timezone('utc', now()) returning d.*;
end;
$$;

create or replace function public.activate_refund_after_wallet(p_deal_id bigint)
returns setof public.deals language plpgsql security definer set search_path = public as $$
begin
    return query update public.deals d set status='refund_requested',
      buyer_wallet_snapshot=coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address),
      buyer_wallet_address=coalesce(d.buyer_wallet_address,d.buyer_wallet_snapshot,u.wallet_address),
      updated_at=timezone('utc', now())
    from public.users u where d.id=p_deal_id and d.buyer_id=u.telegram_id
      and d.status='refund_awaiting_wallet'
      and coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address) is not null returning d.*;
end;
$$;

create or replace function public.resolve_dispute_release(p_deal_id bigint,p_reason text)
returns setof public.deals language plpgsql security definer set search_path = public as $$
declare v_deal public.deals%rowtype;
begin
    select * into v_deal from public.deals where id=p_deal_id for update;
    if not found or v_deal.status<>'disputed' then return; end if;
    update public.deals set status='release_requested',resolution='release',resolution_reason=p_reason,
      updated_at=timezone('utc', now()) where id=p_deal_id returning * into v_deal;
    update public.dispute_tickets set status='resolved_release',resolution='release',
      resolution_reason=p_reason,updated_at=timezone('utc', now())
      where deal_id=p_deal_id and status='open';
    return next v_deal;
end;
$$;

create or replace function public.resolve_dispute_refund(p_deal_id bigint,p_reason text)
returns setof public.deals language plpgsql security definer set search_path = public as $$
declare v_deal public.deals%rowtype; v_wallet text;
begin
    select * into v_deal from public.deals where id=p_deal_id for update;
    if not found or v_deal.status<>'disputed' then return; end if;
    select coalesce(v_deal.buyer_wallet_snapshot,v_deal.buyer_wallet_address,u.wallet_address) into v_wallet
      from public.users u where u.telegram_id=v_deal.buyer_id;
    update public.deals set status=case when v_wallet is null then 'refund_awaiting_wallet' else 'refund_requested' end,
      buyer_wallet_snapshot=coalesce(buyer_wallet_snapshot,buyer_wallet_address,v_wallet),
      buyer_wallet_address=coalesce(buyer_wallet_address,buyer_wallet_snapshot,v_wallet),
      resolution='refund',resolution_reason=p_reason,updated_at=timezone('utc', now())
      where id=p_deal_id returning * into v_deal;
    update public.dispute_tickets set status='resolved_refund',resolution='refund',
      resolution_reason=p_reason,updated_at=timezone('utc', now())
      where deal_id=p_deal_id and status='open';
    return next v_deal;
end;
$$;

create or replace function public.open_deal_dispute(
  p_deal_id bigint,p_actor_id bigint,p_description text
) returns setof public.dispute_tickets language plpgsql security definer set search_path=public as $$
declare v_deal public.deals%rowtype; v_ticket public.dispute_tickets%rowtype;
begin
  if char_length(btrim(p_description)) not between 10 and 1000 then
    raise exception 'dispute description must contain 10 to 1000 characters'; end if;
  select * into v_deal from public.deals where id=p_deal_id for update;
  if not found or (
    p_actor_id<>v_deal.creator_id and p_actor_id is distinct from v_deal.buyer_id
  ) then return; end if;
  if v_deal.status='delivered' and v_deal.inspection_deadline_at<=timezone('utc',now()) then return; end if;
  if v_deal.status not in ('collecting','collection_submitted','delivery_pending','delivered') then return; end if;
  insert into public.dispute_tickets(deal_id,opened_by,description)
    values(p_deal_id,p_actor_id,btrim(p_description))
    on conflict (deal_id) where status='open' do nothing returning * into v_ticket;
  if v_ticket.id is null then return; end if;
  update public.deals set
    status=case when status in ('delivery_pending','delivered') then 'disputed' else status end,
    resolution=null,resolution_reason='Dispute opened; funds frozen pending administrator decision',
    updated_at=timezone('utc',now()) where id=p_deal_id;
  return next v_ticket;
end;
$$;

-- Freeze the buyer destination when custody is first proven. Later profile edits
-- must never redirect an already funded refund.
create or replace function public.mark_direct_custody_confirmed(
    p_deal_id bigint,p_delivery_deadline_at timestamptz
) returns setof public.deals language plpgsql security definer set search_path=public as $$
begin
  return query update public.deals d set
    buyer_wallet_snapshot=coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address),
    buyer_wallet_address=coalesce(d.buyer_wallet_address,d.buyer_wallet_snapshot,u.wallet_address),
    status=case when exists(select 1 from public.dispute_tickets t
          where t.deal_id=d.id and t.status='open') then 'disputed'
      when d.resolution='refund' and coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address) is null
      then 'refund_awaiting_wallet' when d.resolution='refund' then 'refund_requested'
      else 'delivery_pending' end,
    failure_reason=null,custody_confirmed_at=timezone('utc',now()),
    delivery_deadline_at=p_delivery_deadline_at,updated_at=timezone('utc',now())
  from public.users u where d.id=p_deal_id and d.status='collecting'
    and d.currency='USDT' and d.buyer_id=u.telegram_id returning d.*;
end;
$$;

create or replace function public.mark_collection_confirmed(
    p_attempt_id bigint,p_delivery_deadline_at timestamptz
) returns setof public.deals language plpgsql security definer set search_path=public as $$
declare v_deal_id bigint;
begin
  update public.collection_attempts set status='confirmed',confirmed_at=timezone('utc',now()),
    last_checked_at=timezone('utc',now()),updated_at=timezone('utc',now())
    where id=p_attempt_id and status='submitted' returning deal_id into v_deal_id;
  if v_deal_id is null then return; end if;
  return query update public.deals d set
    buyer_wallet_snapshot=coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address),
    buyer_wallet_address=coalesce(d.buyer_wallet_address,d.buyer_wallet_snapshot,u.wallet_address),
    status=case when exists(select 1 from public.dispute_tickets t
          where t.deal_id=d.id and t.status='open') then 'disputed'
      when d.resolution='refund' and coalesce(d.buyer_wallet_snapshot,d.buyer_wallet_address,u.wallet_address) is null
      then 'refund_awaiting_wallet' when d.resolution='refund' then 'refund_requested'
      else 'delivery_pending' end,
    failure_reason=null,custody_confirmed_at=timezone('utc',now()),
    delivery_deadline_at=p_delivery_deadline_at,updated_at=timezone('utc',now())
  from public.users u where d.id=v_deal_id and d.status='collection_submitted'
    and d.buyer_id=u.telegram_id returning d.*;
end;
$$;

alter table public.financial_operations enable row level security;
alter table public.financial_dispatch_lock enable row level security;
alter table public.financial_operation_attempts enable row level security;
alter table public.deposit_scanner_cursors enable row level security;
alter table public.observed_deposits enable row level security;
alter table public.unmatched_payments enable row level security;

revoke all on table public.financial_operations,public.financial_operation_attempts,public.financial_dispatch_lock,
  public.deposit_scanner_cursors,public.observed_deposits,public.unmatched_payments
  from anon,authenticated;
grant select,insert,update on table public.financial_operations,public.financial_operation_attempts,public.financial_dispatch_lock,
  public.deposit_scanner_cursors,public.observed_deposits,public.unmatched_payments to service_role;
grant usage,select on all sequences in schema public to service_role;

revoke all on function public.plan_deal_payout_operations(bigint,text,numeric,text,text,numeric,text,jsonb) from public,anon,authenticated;
revoke all on function public.plan_deal_collection_operation(bigint,text,text,bigint) from public,anon,authenticated;
revoke all on function public.plan_deal_refund_operations(bigint,text,numeric,text,text,numeric,text) from public,anon,authenticated;
revoke all on function public.claim_referral_withdrawal_operation(bigint,text,text,text) from public,anon,authenticated;
revoke all on function public.plan_unmatched_refund_operation(bigint,text,text) from public,anon,authenticated;
revoke all on function public.claim_due_financial_operation(text,integer) from public,anon,authenticated;
revoke all on function public.prepare_financial_operation_attempt(bigint,text,text,timestamptz) from public,anon,authenticated;
revoke all on function public.mark_financial_attempt_submitted(bigint) from public,anon,authenticated;
revoke all on function public.mark_financial_operation_confirmed(bigint,text) from public,anon,authenticated;
revoke all on function public.schedule_financial_operation_retry(bigint,text,boolean,boolean) from public,anon,authenticated;
revoke all on function public.schedule_unprepared_financial_operation_retry(bigint,text) from public,anon,authenticated;
revoke all on function public.reopen_financial_operation(bigint,text) from public,anon,authenticated;
revoke all on function public.mark_financial_operation_manual_review(bigint,text) from public,anon,authenticated;
revoke all on function public.force_complete_financial_operation(bigint,text,text) from public,anon,authenticated;
revoke all on function public.archive_expired_unsuccessful_deals(integer) from public,anon,authenticated;
revoke all on function public.claim_deal_buyer(text,bigint) from public,anon,authenticated;
revoke all on function public.mark_direct_custody_confirmed(bigint,timestamptz) from public,anon,authenticated;
revoke all on function public.mark_collection_confirmed(bigint,timestamptz) from public,anon,authenticated;
revoke all on function public.open_deal_dispute(bigint,bigint,text) from public,anon,authenticated;
revoke all on function public.financial_retry_delay(integer) from public,anon,authenticated;
revoke all on function public.finalize_financial_flow(bigint) from public,anon,authenticated;

grant execute on function public.plan_deal_payout_operations(bigint,text,numeric,text,text,numeric,text,jsonb) to service_role;
grant execute on function public.plan_deal_collection_operation(bigint,text,text,bigint) to service_role;
grant execute on function public.plan_deal_refund_operations(bigint,text,numeric,text,text,numeric,text) to service_role;
grant execute on function public.claim_referral_withdrawal_operation(bigint,text,text,text) to service_role;
grant execute on function public.plan_unmatched_refund_operation(bigint,text,text) to service_role;
grant execute on function public.claim_due_financial_operation(text,integer) to service_role;
grant execute on function public.prepare_financial_operation_attempt(bigint,text,text,timestamptz) to service_role;
grant execute on function public.mark_financial_attempt_submitted(bigint) to service_role;
grant execute on function public.mark_financial_operation_confirmed(bigint,text) to service_role;
grant execute on function public.schedule_financial_operation_retry(bigint,text,boolean,boolean) to service_role;
grant execute on function public.schedule_unprepared_financial_operation_retry(bigint,text) to service_role;
grant execute on function public.reopen_financial_operation(bigint,text) to service_role;
grant execute on function public.mark_financial_operation_manual_review(bigint,text) to service_role;
grant execute on function public.force_complete_financial_operation(bigint,text,text) to service_role;
grant execute on function public.archive_expired_unsuccessful_deals(integer) to service_role;
grant execute on function public.claim_deal_buyer(text,bigint) to service_role;
grant execute on function public.mark_direct_custody_confirmed(bigint,timestamptz) to service_role;
grant execute on function public.mark_collection_confirmed(bigint,timestamptz) to service_role;
grant execute on function public.open_deal_dispute(bigint,bigint,text) to service_role;

notify pgrst, 'reload schema';
commit;
