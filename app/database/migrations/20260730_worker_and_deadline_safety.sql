begin;

-- One hour is sufficient for ordinary offers. Channel ownership transfer can
-- require Telegram security checks and therefore receives a 24-hour SLA.
create or replace function public.deal_stage_timeout(p_deal_type text)
returns interval language sql immutable as $$
  select case when p_deal_type='channel' then interval '24 hours'
              else interval '1 hour' end;
$$;

-- Defence in depth over the human-readable idempotency_key. These indexes
-- prevent a programming error from creating a second semantic payout/refund
-- leg under a different string key.
create unique index if not exists financial_operations_deal_leg_uidx
  on public.financial_operations(deal_id,flow,type)
  where deal_id is not null and flow in ('payout','refund')
    and idempotency_key like 'deal:%';
create unique index if not exists financial_operations_referral_withdrawal_uidx
  on public.financial_operations(referral_withdrawal_id)
  where referral_withdrawal_id is not null;
create unique index if not exists financial_operations_unmatched_leg_uidx
  on public.financial_operations(unmatched_payment_id,flow,type)
  where unmatched_payment_id is not null;
create unique index if not exists financial_operations_deal_collection_uidx
  on public.financial_operations(deal_id)
  where flow='collection' and metadata->>'purpose'='deal_custody';

create or replace function public.claim_deal_buyer(p_public_id text,p_buyer_id bigint)
returns setof public.deals language plpgsql security definer set search_path=public as $$
declare v_deal public.deals%rowtype; v_wallet text; v_timeout interval;
begin
  select * into v_deal from public.deals where public_id=p_public_id for update;
  if not found or v_deal.status<>'pending' or v_deal.creator_id=p_buyer_id then return; end if;
  if v_deal.buyer_id is not null and v_deal.buyer_id<>p_buyer_id then return; end if;
  v_timeout:=public.deal_stage_timeout(v_deal.deal_type);
  if coalesce(v_deal.payment_deadline_at,v_deal.created_at+v_timeout)<=timezone('utc',now()) then
    update public.deals set status='cancelled',resolution='timeout',
      resolution_reason='Payment deadline expired',updated_at=timezone('utc',now())
      where id=v_deal.id and status='pending';
    return;
  end if;
  select wallet_address into v_wallet from public.users where telegram_id=p_buyer_id;
  if v_wallet is null then return; end if;
  if v_deal.buyer_id is null then
    update public.deals set buyer_id=p_buyer_id,buyer_wallet_address=v_wallet,
      buyer_wallet_snapshot=v_wallet,payment_deadline_at=timezone('utc',now())+v_timeout,
      updated_at=timezone('utc',now()) where id=v_deal.id returning * into v_deal;
  elsif v_deal.payment_deadline_at is null then
    update public.deals set payment_deadline_at=timezone('utc',now())+v_timeout,
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
    and coalesce(d.payment_deadline_at,d.created_at+public.deal_stage_timeout(d.deal_type))
        <=timezone('utc',now())
    and not exists(select 1 from public.deal_payments p where p.deal_id=d.id);
  get diagnostics v_count=row_count;
  return v_count;
end;
$$;

-- The blockchain timestamp, not scheduler order, decides an exact payment at
-- the deadline. An on-time payment continues even if the timeout worker won
-- the row lock first. A genuinely late payment is collected for a safe refund.
create or replace function public.claim_deal_payment(
  p_deal_id bigint,p_tx_hash text,p_tx_lt numeric,p_amount_atomic numeric,
  p_sender text,p_memo_missing boolean,p_observed_at timestamptz
) returns setof public.deals
language plpgsql security definer set search_path=public as $$
declare
  v_deal public.deals%rowtype;
  v_payment_id bigint;
  v_deadline timestamptz;
  v_late boolean;
begin
  select * into v_deal from public.deals where id=p_deal_id for update;
  if not found or v_deal.status not in ('pending','cancelled') or v_deal.buyer_id is null then return; end if;
  v_deadline:=coalesce(
    v_deal.payment_deadline_at,
    v_deal.created_at+public.deal_stage_timeout(v_deal.deal_type)
  );
  v_late:=p_observed_at>v_deadline
    or (v_deal.status='cancelled' and v_deal.resolution is distinct from 'timeout');
  insert into public.deal_payments(deal_id,tx_hash,tx_lt,amount_atomic,sender,observed_at)
  values(p_deal_id,p_tx_hash,p_tx_lt,p_amount_atomic,p_sender,p_observed_at)
  on conflict do nothing returning id into v_payment_id;
  if v_payment_id is null then return; end if;
  update public.deals set status='collecting',paid_tx_hash=p_tx_hash,paid_tx_lt=p_tx_lt,
    paid_amount_atomic=p_amount_atomic,payment_sender=p_sender,payment_memo_missing=p_memo_missing,
    resolution=case when v_late then 'refund' else null end,
    resolution_reason=case when v_late then 'Payment observed after deadline; automatic refund after custody'
                           else null end,
    paid_at=p_observed_at,updated_at=timezone('utc',now())
  where id=p_deal_id returning * into v_deal;
  return next v_deal;
end;
$$;

-- Normalize custody deadlines even when an older function passes a hard-coded
-- one-hour value. This also covers direct USDT custody.
create or replace function public.apply_deal_type_delivery_deadline()
returns trigger language plpgsql set search_path=public as $$
begin
  if new.status='delivery_pending'
     and (old.custody_confirmed_at is distinct from new.custody_confirmed_at
          or old.status is distinct from new.status) then
    new.delivery_deadline_at:=timezone('utc',now())+public.deal_stage_timeout(new.deal_type);
  end if;
  return new;
end;
$$;
drop trigger if exists deals_type_delivery_deadline_trg on public.deals;
create trigger deals_type_delivery_deadline_trg
before update on public.deals for each row
execute function public.apply_deal_type_delivery_deadline();

revoke all on function public.deal_stage_timeout(text) from public,anon,authenticated;
revoke all on function public.claim_deal_buyer(text,bigint) from public,anon,authenticated;
revoke all on function public.cancel_expired_pending_deals() from public,anon,authenticated;
revoke all on function public.claim_deal_payment(bigint,text,numeric,numeric,text,boolean,timestamptz)
  from public,anon,authenticated;
grant execute on function public.deal_stage_timeout(text) to service_role;
grant execute on function public.claim_deal_buyer(text,bigint) to service_role;
grant execute on function public.cancel_expired_pending_deals() to service_role;
grant execute on function public.claim_deal_payment(bigint,text,numeric,numeric,text,boolean,timestamptz)
  to service_role;

notify pgrst,'reload schema';
commit;
