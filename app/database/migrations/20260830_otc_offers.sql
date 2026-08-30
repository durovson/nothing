begin;

create table if not exists public.otc_offers (
    id bigint generated always as identity primary key,
    listing_id bigint not null references public.desk_listings(id) on delete restrict,
    listing_public_id text not null,
    listing_description text not null,
    seller_id bigint not null references public.users(telegram_id) on delete restrict,
    seller_language text not null default 'ru' check (seller_language in ('ru','en')),
    buyer_id bigint not null references public.users(telegram_id) on delete restrict,
    buyer_username text,
    buyer_language text not null default 'ru' check (buyer_language in ('ru','en')),
    amount numeric(36,9) not null check (amount > 0),
    status text not null default 'pending' check (
        status in ('pending','accepted','declined')
    ),
    responded_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    check (seller_id <> buyer_id)
);

create index if not exists otc_offers_seller_pending_idx
    on public.otc_offers(seller_id, created_at desc)
    where status = 'pending';
create index if not exists otc_offers_buyer_idx
    on public.otc_offers(buyer_id, created_at desc);

alter table public.otc_offers enable row level security;
revoke all on table public.otc_offers from public, anon, authenticated;
grant select, insert, update on table public.otc_offers to service_role;
grant usage, select on sequence public.otc_offers_id_seq to service_role;

create or replace function public.create_otc_offer(
    p_listing_public_id text,
    p_buyer_id bigint,
    p_buyer_username text,
    p_buyer_language text,
    p_amount numeric
) returns setof public.otc_offers
language plpgsql security definer set search_path = public as $$
declare
    v_listing public.desk_listings%rowtype;
begin
    select * into v_listing
      from public.desk_listings
     where public_id = p_listing_public_id
       and status = 'published'
     for share;

    if not found or v_listing.owner_id = p_buyer_id then
        return;
    end if;

    return query insert into public.otc_offers(
        listing_id,
        listing_public_id,
        listing_description,
        seller_id,
        seller_language,
        buyer_id,
        buyer_username,
        buyer_language,
        amount
    ) values (
        v_listing.id,
        v_listing.public_id,
        v_listing.description,
        v_listing.owner_id,
        v_listing.owner_language,
        p_buyer_id,
        nullif(ltrim(btrim(p_buyer_username), '@'), ''),
        p_buyer_language,
        p_amount
    ) returning *;
end;
$$;

create or replace function public.resolve_otc_offer(
    p_offer_id bigint,
    p_seller_id bigint,
    p_status text
) returns setof public.otc_offers
language plpgsql security definer set search_path = public as $$
begin
    if p_status not in ('accepted', 'declined') then
        raise exception 'invalid OTC offer status';
    end if;

    return query update public.otc_offers
       set status = p_status,
           responded_at = timezone('utc', now()),
           updated_at = timezone('utc', now())
     where id = p_offer_id
       and seller_id = p_seller_id
       and status = 'pending'
     returning *;
end;
$$;

revoke all on function public.create_otc_offer(text,bigint,text,text,numeric)
    from public, anon, authenticated;
revoke all on function public.resolve_otc_offer(bigint,bigint,text)
    from public, anon, authenticated;
grant execute on function public.create_otc_offer(text,bigint,text,text,numeric)
    to service_role;
grant execute on function public.resolve_otc_offer(bigint,bigint,text)
    to service_role;

commit;
