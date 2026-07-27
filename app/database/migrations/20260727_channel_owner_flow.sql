begin;

drop function if exists public.mark_channel_access_granted(bigint);
drop function if exists public.request_channel_release_after_access(bigint);

alter table public.deals add column if not exists channel_id bigint;
alter table public.deals add column if not exists channel_title text;
alter table public.deals add column if not exists channel_username text;
alter table public.deals add column if not exists channel_access_granted_at timestamptz;
alter table public.deals add column if not exists channel_access_error text;
alter table public.deals add column if not exists channel_owner_verified_at timestamptz;
alter table public.deals add column if not exists channel_last_member_status text;
alter table public.deals add column if not exists channel_last_checked_at timestamptz;

alter table public.deals drop constraint if exists deals_deal_type_check;
alter table public.deals add constraint deals_deal_type_check
    check (deal_type in ('offer', 'gifts', 'channel', 'account'));

alter table public.deals drop constraint if exists deals_channel_member_status_check;
alter table public.deals add constraint deals_channel_member_status_check check (
    channel_last_member_status is null
    or channel_last_member_status in ('creator', 'administrator', 'member', 'absent', 'unknown')
);

drop index if exists public.deals_channel_access_pending_idx;
create index deals_channel_access_pending_idx
    on public.deals(id)
    where deal_type = 'channel'
      and status = 'delivery_pending'
      and channel_owner_verified_at is null
      and buyer_id is not null;

create or replace function public.mark_deal_delivered(
    p_deal_id bigint,
    p_seller_id bigint,
    p_inspection_deadline_at timestamptz
) returns setof public.deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update public.deals
    set status = 'delivered', delivered_at = timezone('utc', now()),
        inspection_deadline_at = p_inspection_deadline_at,
        updated_at = timezone('utc', now())
    where id = p_deal_id and creator_id = p_seller_id
      and status = 'delivery_pending'
      and deal_type <> 'channel'
      and delivery_deadline_at > timezone('utc', now())
    returning *;
end;
$$;

create or replace function public.confirm_channel_owner_transfer(p_deal_id bigint)
returns setof public.deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update public.deals set
        status = 'release_requested',
        channel_owner_verified_at = coalesce(channel_owner_verified_at, timezone('utc', now())),
        channel_access_granted_at = coalesce(channel_access_granted_at, timezone('utc', now())),
        channel_last_member_status = 'creator',
        channel_last_checked_at = timezone('utc', now()),
        channel_access_error = null,
        updated_at = timezone('utc', now())
    where id = p_deal_id and deal_type = 'channel'
      and status = 'delivery_pending' and buyer_id is not null
    returning *;
end;
$$;

create or replace function public.dispute_expired_channel_transfer(
    p_deal_id bigint,
    p_reason text
)
returns setof public.deals
language plpgsql security definer set search_path = public
as $$
declare
    v_deal public.deals%rowtype;
begin
    update public.deals set
        status = 'disputed', resolution_reason = p_reason,
        updated_at = timezone('utc', now())
    where id = p_deal_id and deal_type = 'channel'
      and status = 'delivery_pending' and buyer_id is not null
      and channel_owner_verified_at is null
      and delivery_deadline_at <= timezone('utc', now())
    returning * into v_deal;
    if not found then return; end if;
    if not exists (
        select 1 from public.dispute_tickets
        where deal_id = v_deal.id and status = 'open'
    ) then
        insert into public.dispute_tickets(deal_id, opened_by, status, description)
        values (
            v_deal.id, v_deal.buyer_id, 'open',
            left('Automatic channel ownership verification failed: ' || p_reason, 1000)
        );
    end if;
    return next v_deal;
end;
$$;

revoke all on function public.confirm_channel_owner_transfer(bigint)
    from public, anon, authenticated;
revoke all on function public.dispute_expired_channel_transfer(bigint, text)
    from public, anon, authenticated;
grant execute on function public.confirm_channel_owner_transfer(bigint) to service_role;
grant execute on function public.dispute_expired_channel_transfer(bigint, text) to service_role;

notify pgrst, 'reload schema';
commit;
