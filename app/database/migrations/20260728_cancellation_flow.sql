begin;

alter table public.deals add column if not exists cancellation_requested_at timestamptz;

create or replace function public.request_deal_cancellation(p_deal_id bigint, p_actor_id bigint)
returns setof public.deals
language plpgsql security definer set search_path = public
as $$
declare v_deal public.deals%rowtype;
begin
    select * into v_deal from public.deals where id = p_deal_id for update;
    if not found or (p_actor_id <> v_deal.creator_id
        and p_actor_id is distinct from v_deal.buyer_id) then return; end if;
    if v_deal.status = 'pending' then
        update public.deals set status='cancelled', resolution='cancel',
            resolution_reason='Cancelled by participant',
            cancellation_requested_at=timezone('utc', now()), updated_at=timezone('utc', now())
        where id=p_deal_id returning * into v_deal;
    elsif v_deal.status in ('collecting','collection_submitted') then
        update public.deals set resolution='refund',
            resolution_reason='Cancelled while custody was being confirmed',
            cancellation_requested_at=timezone('utc', now()), updated_at=timezone('utc', now())
        where id=p_deal_id returning * into v_deal;
    elsif v_deal.status in ('delivery_pending','delivered') then
        update public.deals as d set status=case when u.wallet_address is null
                then 'refund_awaiting_wallet' else 'refund_requested' end,
            resolution='refund', resolution_reason='Cancelled by participant',
            cancellation_requested_at=timezone('utc', now()), updated_at=timezone('utc', now())
        from public.users as u
        where d.id=p_deal_id and d.buyer_id=u.telegram_id returning d.* into v_deal;
    else
        return;
    end if;
    return next v_deal;
end;
$$;

create or replace function public.claim_deal_payment(
    p_deal_id bigint, p_tx_hash text, p_tx_lt numeric, p_amount_atomic numeric,
    p_sender text, p_memo_missing boolean, p_observed_at timestamptz
) returns setof public.deals
language plpgsql security definer set search_path = public
as $$
declare v_deal public.deals%rowtype; v_payment_id bigint;
begin
    select * into v_deal from public.deals where id=p_deal_id for update;
    if not found or v_deal.status not in ('pending','cancelled') or v_deal.buyer_id is null then return; end if;
    insert into public.deal_payments(deal_id,tx_hash,tx_lt,amount_atomic,sender,observed_at)
    values(p_deal_id,p_tx_hash,p_tx_lt,p_amount_atomic,p_sender,p_observed_at)
    on conflict do nothing returning id into v_payment_id;
    if v_payment_id is null then return; end if;
    update public.deals set status='collecting', paid_tx_hash=p_tx_hash, paid_tx_lt=p_tx_lt,
        paid_amount_atomic=p_amount_atomic, payment_sender=p_sender,
        payment_memo_missing=p_memo_missing,
        resolution=case when v_deal.status='cancelled' then 'refund' else resolution end,
        resolution_reason=case when v_deal.status='cancelled'
            then coalesce(resolution_reason,'Payment detected after cancellation') else resolution_reason end,
        paid_at=p_observed_at, updated_at=timezone('utc', now())
    where id=p_deal_id returning * into v_deal;
    return next v_deal;
end;
$$;

create or replace function public.mark_direct_custody_confirmed(
    p_deal_id bigint, p_delivery_deadline_at timestamptz
) returns setof public.deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update public.deals as d set status=case
            when d.resolution='refund' and u.wallet_address is null then 'refund_awaiting_wallet'
            when d.resolution='refund' then 'refund_requested' else 'delivery_pending' end,
        failure_reason=null, custody_confirmed_at=timezone('utc', now()),
        delivery_deadline_at=p_delivery_deadline_at, updated_at=timezone('utc', now())
    from public.users as u
    where d.id=p_deal_id and d.status='collecting' and d.currency='USDT'
      and d.buyer_id=u.telegram_id returning d.*;
end;
$$;

create or replace function public.mark_collection_confirmed(
    p_attempt_id bigint, p_delivery_deadline_at timestamptz
) returns setof public.deals
language plpgsql security definer set search_path = public
as $$
declare v_deal_id bigint;
begin
    update public.collection_attempts set status='confirmed', confirmed_at=timezone('utc', now()),
        last_checked_at=timezone('utc', now()), updated_at=timezone('utc', now())
    where id=p_attempt_id and status='submitted' returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query update public.deals as d set status=case
            when d.resolution='refund' and u.wallet_address is null then 'refund_awaiting_wallet'
            when d.resolution='refund' then 'refund_requested' else 'delivery_pending' end,
        failure_reason=null, custody_confirmed_at=timezone('utc', now()),
        delivery_deadline_at=p_delivery_deadline_at, updated_at=timezone('utc', now())
    from public.users as u
    where d.id=v_deal_id and d.status='collection_submitted'
      and d.buyer_id=u.telegram_id returning d.*;
end;
$$;

revoke all on function public.request_deal_cancellation(bigint,bigint) from public,anon,authenticated;
grant execute on function public.request_deal_cancellation(bigint,bigint) to service_role;
notify pgrst, 'reload schema';
commit;
