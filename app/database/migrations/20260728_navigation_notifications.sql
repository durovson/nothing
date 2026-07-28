begin;

alter table public.deals add column if not exists buyer_join_notified_at timestamptz;

create or replace function public.claim_deal_join_notification(p_deal_id bigint)
returns setof public.deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update public.deals
    set buyer_join_notified_at = timezone('utc', now())
    where id = p_deal_id and buyer_id is not null
      and buyer_join_notified_at is null
    returning *;
end;
$$;

revoke all on function public.claim_deal_join_notification(bigint)
    from public, anon, authenticated;
grant execute on function public.claim_deal_join_notification(bigint) to service_role;

notify pgrst, 'reload schema';
commit;
