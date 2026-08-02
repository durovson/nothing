begin;

-- One bounded, concurrency-safe database round trip replaces the lifecycle
-- worker's four table scans and one RPC call per matching deal.
create or replace function public.process_deal_lifecycle_batch(p_limit integer default 50)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_limit integer := least(greatest(coalesce(p_limit, 50), 1), 200);
    v_cancelled_pending bigint := 0;
    v_delivery_refunds bigint := 0;
    v_inspection_releases bigint := 0;
    v_wallet_refunds_activated bigint := 0;
begin
    with candidates as (
        select d.id
        from public.deals as d
        where d.status = 'pending'
          and d.paid_tx_hash is null
          and coalesce(
                d.payment_deadline_at,
                d.created_at + public.deal_stage_timeout(d.deal_type)
              ) <= timezone('utc', now())
          and not exists (
              select 1 from public.deal_payments as p where p.deal_id = d.id
          )
        order by coalesce(
            d.payment_deadline_at,
            d.created_at + public.deal_stage_timeout(d.deal_type)
        ), d.id
        for update of d skip locked
        limit v_limit
    ), updated as (
        update public.deals as d
        set status = 'cancelled',
            resolution = 'timeout',
            resolution_reason = 'Payment deadline expired',
            updated_at = timezone('utc', now())
        from candidates as c
        where d.id = c.id
          and d.status = 'pending'
          and d.paid_tx_hash is null
          and not exists (
              select 1 from public.deal_payments as p where p.deal_id = d.id
          )
        returning d.id
    )
    select count(*) into v_cancelled_pending from updated;

    with candidates as (
        select
            d.id,
            coalesce(d.buyer_wallet_snapshot, d.buyer_wallet_address, u.wallet_address) as refund_wallet
        from public.deals as d
        left join public.users as u on u.telegram_id = d.buyer_id
        where d.status = 'delivery_pending'
          and d.deal_type <> 'channel'
          and d.delivery_deadline_at <= timezone('utc', now())
        order by d.delivery_deadline_at, d.id
        for update of d skip locked
        limit v_limit
    ), updated as (
        update public.deals as d
        set status = case
                when c.refund_wallet is null then 'refund_awaiting_wallet'
                else 'refund_requested'
            end,
            buyer_wallet_snapshot = coalesce(d.buyer_wallet_snapshot, c.refund_wallet),
            buyer_wallet_address = coalesce(d.buyer_wallet_address, c.refund_wallet),
            resolution = 'refund',
            resolution_reason = 'Seller delivery deadline expired',
            updated_at = timezone('utc', now())
        from candidates as c
        where d.id = c.id and d.status = 'delivery_pending'
        returning d.id
    )
    select count(*) into v_delivery_refunds from updated;

    with candidates as (
        select d.id
        from public.deals as d
        where d.status = 'delivered'
          and d.inspection_deadline_at <= timezone('utc', now())
        order by d.inspection_deadline_at, d.id
        for update of d skip locked
        limit v_limit
    ), updated as (
        update public.deals as d
        set status = 'release_requested',
            resolution = 'auto_release',
            resolution_reason = 'Buyer inspection deadline expired',
            updated_at = timezone('utc', now())
        from candidates as c
        where d.id = c.id and d.status = 'delivered'
        returning d.id
    )
    select count(*) into v_inspection_releases from updated;

    with candidates as (
        select
            d.id,
            coalesce(d.buyer_wallet_snapshot, d.buyer_wallet_address, u.wallet_address) as refund_wallet
        from public.deals as d
        left join public.users as u on u.telegram_id = d.buyer_id
        where d.status = 'refund_awaiting_wallet'
          and coalesce(d.buyer_wallet_snapshot, d.buyer_wallet_address, u.wallet_address) is not null
        order by d.id
        for update of d skip locked
        limit v_limit
    ), updated as (
        update public.deals as d
        set status = 'refund_requested',
            buyer_wallet_snapshot = coalesce(d.buyer_wallet_snapshot, c.refund_wallet),
            buyer_wallet_address = coalesce(d.buyer_wallet_address, c.refund_wallet),
            updated_at = timezone('utc', now())
        from candidates as c
        where d.id = c.id and d.status = 'refund_awaiting_wallet'
        returning d.id
    )
    select count(*) into v_wallet_refunds_activated from updated;

    return jsonb_build_object(
        'cancelled_pending', v_cancelled_pending,
        'delivery_refunds', v_delivery_refunds,
        'inspection_releases', v_inspection_releases,
        'wallet_refunds_activated', v_wallet_refunds_activated
    );
end;
$$;

create index if not exists deals_lifecycle_payment_deadline_idx
    on public.deals(payment_deadline_at, id)
    where status = 'pending' and paid_tx_hash is null;

create index if not exists deals_lifecycle_delivery_deadline_idx
    on public.deals(delivery_deadline_at, id)
    where status = 'delivery_pending' and deal_type <> 'channel';

create index if not exists deals_lifecycle_inspection_deadline_idx
    on public.deals(inspection_deadline_at, id)
    where status = 'delivered';

create index if not exists deals_refund_awaiting_wallet_idx
    on public.deals(buyer_id, id)
    where status = 'refund_awaiting_wallet';

revoke all on function public.process_deal_lifecycle_batch(integer)
    from public, anon, authenticated;
grant execute on function public.process_deal_lifecycle_batch(integer) to service_role;

notify pgrst, 'reload schema';

commit;
