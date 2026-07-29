begin;

do $$
begin
    if not exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'deals'
          and column_name = 'success_feed_notified_at'
    ) then
        alter table public.deals add column success_feed_notified_at timestamptz;

        -- Do not flood the public channel with deals completed before this feature.
        update public.deals
        set success_feed_notified_at = coalesce(updated_at, timezone('utc', now()))
        where status = 'completed';
    end if;
end;
$$;

create index if not exists deals_success_feed_pending_idx on public.deals(id)
where status = 'completed' and success_feed_notified_at is null;

create or replace function public.claim_success_feed_notification(p_deal_id bigint)
returns setof public.deals
language plpgsql
security definer
set search_path = public
as $$
begin
    return query
    update public.deals
    set success_feed_notified_at = timezone('utc', now())
    where id = p_deal_id
      and status = 'completed'
      and success_feed_notified_at is null
    returning *;
end;
$$;

create or replace function public.release_success_feed_notification(p_deal_id bigint)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.deals
    set success_feed_notified_at = null
    where id = p_deal_id
      and status = 'completed';
end;
$$;

revoke all on function public.claim_success_feed_notification(bigint)
    from public, anon, authenticated;
revoke all on function public.release_success_feed_notification(bigint)
    from public, anon, authenticated;
grant execute on function public.claim_success_feed_notification(bigint) to service_role;
grant execute on function public.release_success_feed_notification(bigint) to service_role;

notify pgrst, 'reload schema';
commit;
