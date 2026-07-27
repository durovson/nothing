begin;

alter table public.deals add column if not exists channel_id bigint;
alter table public.deals add column if not exists channel_title text;
alter table public.deals add column if not exists channel_username text;
alter table public.deals add column if not exists channel_access_granted_at timestamptz;
alter table public.deals add column if not exists channel_access_error text;

alter table public.deals drop constraint if exists deals_deal_type_check;
alter table public.deals add constraint deals_deal_type_check
    check (deal_type in ('offer', 'gifts', 'channel', 'account'));

alter table public.deals drop constraint if exists deals_channel_metadata_check;
alter table public.deals add constraint deals_channel_metadata_check check (
    deal_type <> 'channel'
    or (channel_id is not null and nullif(btrim(channel_title), '') is not null)
) not valid;

alter table public.deals drop constraint if exists deals_channel_access_error_length_check;
alter table public.deals add constraint deals_channel_access_error_length_check
    check (channel_access_error is null or char_length(channel_access_error) <= 1000);

create index if not exists deals_channel_access_pending_idx
    on public.deals(id)
    where deal_type = 'channel'
      and status = 'delivery_pending'
      and channel_access_granted_at is null
      and buyer_id is not null;

create or replace function public.mark_channel_access_granted(p_deal_id bigint)
returns setof public.deals
language plpgsql
security definer
set search_path = public
as $$
begin
    return query update public.deals set
        channel_access_granted_at = coalesce(channel_access_granted_at, timezone('utc', now())),
        channel_access_error = null,
        updated_at = timezone('utc', now())
    where id = p_deal_id
      and deal_type = 'channel'
      and status = 'delivery_pending'
      and buyer_id is not null
    returning *;
end;
$$;

create or replace function public.request_channel_release_after_access(p_deal_id bigint)
returns setof public.deals
language plpgsql
security definer
set search_path = public
as $$
begin
    return query update public.deals set
        status = 'release_requested',
        updated_at = timezone('utc', now())
    where id = p_deal_id
      and deal_type = 'channel'
      and status = 'delivery_pending'
      and channel_access_granted_at is not null
      and buyer_id is not null
    returning *;
end;
$$;

revoke all on function public.mark_channel_access_granted(bigint)
    from public, anon, authenticated;
revoke all on function public.request_channel_release_after_access(bigint)
    from public, anon, authenticated;
grant execute on function public.mark_channel_access_granted(bigint) to service_role;
grant execute on function public.request_channel_release_after_access(bigint) to service_role;

notify pgrst, 'reload schema';

commit;
