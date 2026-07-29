begin;

alter table public.financial_operations
  drop constraint if exists financial_operations_flow_check;
alter table public.financial_operations add constraint financial_operations_flow_check
  check(flow in ('collection','payout','refund','referral','unmatched_refund'));
alter table public.financial_operations
  drop constraint if exists financial_operations_type_check;
alter table public.financial_operations add constraint financial_operations_type_check
  check(type in ('collection_transfer','seller_transfer','buyer_refund','service_fee_transfer','referral_transfer'));

alter table public.deals add column if not exists payment_deadline_at timestamptz;
create index if not exists deals_payment_deadline_idx
  on public.deals(payment_deadline_at,id) where status='pending';

create table if not exists public.system_settings (
  key text primary key,
  value text not null,
  reason text,
  automatic boolean not null default false,
  updated_by bigint,
  updated_at timestamptz not null default timezone('utc',now()),
  check (key<>'system_mode' or value in ('normal','read_only','emergency')),
  check (reason is null or char_length(reason)<=1000)
);
insert into public.system_settings(key,value,reason,automatic)
values('system_mode','normal','Initial mode',false)
on conflict(key) do nothing;

create or replace function public.set_system_mode(
  p_mode text,p_reason text,p_updated_by bigint default null,p_automatic boolean default false
) returns setof public.system_settings
language plpgsql security definer set search_path=public as $$
declare v_current public.system_settings%rowtype;
begin
  if p_mode not in ('normal','read_only','emergency') then
    raise exception 'unsupported system mode';
  end if;
  if p_automatic and p_mode='emergency' then
    raise exception 'emergency mode is manual only';
  end if;
  select * into v_current from public.system_settings where key='system_mode' for update;
  if v_current.value='emergency' and p_automatic then return next v_current; return; end if;
  return query update public.system_settings set value=p_mode,reason=left(nullif(btrim(p_reason),''),1000),
    automatic=p_automatic,updated_by=p_updated_by,updated_at=timezone('utc',now())
    where key='system_mode' returning *;
end;
$$;

create or replace function public.claim_deal_buyer(p_public_id text,p_buyer_id bigint)
returns setof public.deals language plpgsql security definer set search_path=public as $$
declare v_deal public.deals%rowtype; v_wallet text;
begin
  select * into v_deal from public.deals where public_id=p_public_id for update;
  if not found or v_deal.status<>'pending' or v_deal.creator_id=p_buyer_id then return; end if;
  if v_deal.buyer_id is not null and v_deal.buyer_id<>p_buyer_id then return; end if;
  if coalesce(v_deal.payment_deadline_at,v_deal.created_at+interval '1 hour')<=timezone('utc',now()) then
    update public.deals set status='cancelled',resolution='timeout',
      resolution_reason='Payment deadline expired',updated_at=timezone('utc',now())
      where id=v_deal.id and status='pending';
    return;
  end if;
  select wallet_address into v_wallet from public.users where telegram_id=p_buyer_id;
  if v_wallet is null then return; end if;
  if v_deal.buyer_id is null then
    update public.deals set buyer_id=p_buyer_id,buyer_wallet_address=v_wallet,
      buyer_wallet_snapshot=v_wallet,payment_deadline_at=timezone('utc',now())+interval '1 hour',
      updated_at=timezone('utc',now()) where id=v_deal.id returning * into v_deal;
  elsif v_deal.payment_deadline_at is null then
    update public.deals set payment_deadline_at=timezone('utc',now())+interval '1 hour',
      updated_at=timezone('utc',now()) where id=v_deal.id returning * into v_deal;
  end if;
  return next v_deal;
end;
$$;

create or replace function public.cancel_expired_pending_deals()
returns bigint language plpgsql security definer set search_path=public as $$
declare v_count bigint;
begin
  update public.deals d set status='cancelled',resolution='timeout',
    resolution_reason='Payment deadline expired',updated_at=timezone('utc',now())
  where d.status='pending' and d.paid_tx_hash is null
    and coalesce(d.payment_deadline_at,d.created_at+interval '1 hour')<=timezone('utc',now())
    and not exists(select 1 from public.deal_payments p where p.deal_id=d.id);
  get diagnostics v_count=row_count;
  return v_count;
end;
$$;

alter table public.system_settings enable row level security;
revoke all on table public.system_settings from public,anon,authenticated;
grant select,insert,update on table public.system_settings to service_role;
revoke all on function public.set_system_mode(text,text,bigint,boolean) from public,anon,authenticated;
revoke all on function public.cancel_expired_pending_deals() from public,anon,authenticated;
grant execute on function public.set_system_mode(text,text,bigint,boolean) to service_role;
grant execute on function public.cancel_expired_pending_deals() to service_role;
grant execute on function public.claim_deal_buyer(text,bigint) to service_role;

notify pgrst,'reload schema';
commit;
