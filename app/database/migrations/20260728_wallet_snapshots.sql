begin;

alter table public.deals add column if not exists seller_wallet_address text;
alter table public.deals add column if not exists buyer_wallet_address text;
alter table public.deals add column if not exists payout_tx_hash text;

drop function if exists public.mark_payout_confirmed(bigint);

create or replace function public.mark_payout_confirmed(
    p_attempt_id bigint,
    p_transaction_hash text
)
returns setof public.deals
language plpgsql security definer set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    if nullif(btrim(p_transaction_hash), '') is null then return; end if;
    update public.payout_attempts
    set status='confirmed', confirmed_at=timezone('utc', now()),
        last_checked_at=timezone('utc', now()), updated_at=timezone('utc', now())
    where id=p_attempt_id and status='submitted'
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query update public.deals set status='completed', failure_reason=null,
        payout_tx_hash=p_transaction_hash, updated_at=timezone('utc', now())
    where id=v_deal_id and status='payout_submitted' returning *;
end;
$$;

update public.deals as d
set seller_wallet_address = u.wallet_address
from public.users as u
where d.creator_id = u.telegram_id and d.seller_wallet_address is null;

update public.deals as d
set buyer_wallet_address = u.wallet_address
from public.users as u
where d.buyer_id = u.telegram_id and d.buyer_wallet_address is null;

create or replace function public.claim_deal_buyer(p_public_id text, p_buyer_id bigint)
returns setof public.deals
language plpgsql security definer set search_path = public
as $$
declare
    v_deal public.deals%rowtype;
    v_buyer_wallet text;
begin
    select * into v_deal from public.deals where public_id = p_public_id for update;
    if not found or v_deal.status <> 'pending' or v_deal.creator_id = p_buyer_id then
        return;
    end if;
    if v_deal.buyer_id is not null and v_deal.buyer_id <> p_buyer_id then
        return;
    end if;
    select wallet_address into v_buyer_wallet
    from public.users where telegram_id = p_buyer_id;
    if v_buyer_wallet is null then return; end if;
    if v_deal.buyer_id is null then
        update public.deals set buyer_id = p_buyer_id,
            buyer_wallet_address = v_buyer_wallet,
            updated_at = timezone('utc', now())
        where id = v_deal.id returning * into v_deal;
    end if;
    return next v_deal;
end;
$$;

revoke all on function public.claim_deal_buyer(text,bigint) from public,anon,authenticated;
grant execute on function public.claim_deal_buyer(text,bigint) to service_role;
revoke all on function public.mark_payout_confirmed(bigint,text) from public,anon,authenticated;
grant execute on function public.mark_payout_confirmed(bigint,text) to service_role;
notify pgrst, 'reload schema';
commit;
