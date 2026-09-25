begin;

-- Reuse the holder-community registry instead of adding another community table.
-- `enabled` remains the Holder-referral switch; Desk moderation is independent.
alter table public.referral_communities
    add column if not exists telegram_username text,
    add column if not exists desk_topic_id bigint,
    add column if not exists desk_enabled boolean not null default false;

alter table public.desk_listings
    add column if not exists source_type text not null default 'paid',
    add column if not exists description_html text,
    add column if not exists community_id bigint
        references public.referral_communities(id) on delete restrict,
    add column if not exists source_chat_id bigint,
    add column if not exists source_topic_id bigint,
    add column if not exists source_message_id bigint,
    add column if not exists item_fingerprint text,
    add column if not exists community_name text,
    add column if not exists community_username text;

alter table public.desk_listings
    drop constraint if exists desk_listings_publication_fee_check,
    drop constraint if exists desk_listings_publication_fee_atomic_check,
    drop constraint if exists desk_listings_source_type_check,
    drop constraint if exists desk_listings_publication_fee_by_source_check,
    drop constraint if exists desk_listings_community_source_check;

alter table public.desk_listings
    add constraint desk_listings_source_type_check
        check (source_type in ('paid', 'community')),
    add constraint desk_listings_publication_fee_by_source_check
        check (
            (source_type = 'paid' and publication_fee > 0 and publication_fee_atomic > 0)
            or
            (source_type = 'community' and publication_fee = 0 and publication_fee_atomic = 0)
        ),
    add constraint desk_listings_community_source_check
        check (
            source_type <> 'community'
            or (
                community_id is not null
                and source_chat_id is not null
                and source_topic_id is not null
                and source_message_id is not null
                and item_fingerprint ~ '^[0-9a-f]{64}$'
            )
        );

create unique index if not exists desk_listings_community_source_message_idx
    on public.desk_listings(community_id, source_message_id)
    where source_type = 'community';

-- A normalized visible Item can be active only once globally, so forwarding the
-- same advert from several connected communities cannot duplicate the GRNT post.
create unique index if not exists desk_listings_active_community_item_idx
    on public.desk_listings(item_fingerprint)
    where source_type = 'community' and status in ('publishing', 'published');

create or replace function public.connect_community_desk(
    p_telegram_chat_id bigint,
    p_desk_topic_id bigint,
    p_name text,
    p_telegram_username text,
    p_owner_user_id bigint
) returns setof public.referral_communities
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_desk_topic_id is null or p_desk_topic_id <= 0 then
        return;
    end if;
    return query
    insert into public.referral_communities(
        name,
        telegram_chat_id,
        telegram_username,
        desk_topic_id,
        owner_user_id,
        enabled,
        desk_enabled
    ) values (
        left(btrim(p_name), 120),
        p_telegram_chat_id,
        nullif(lower(ltrim(btrim(p_telegram_username), '@')), ''),
        p_desk_topic_id,
        p_owner_user_id,
        false,
        false
    )
    on conflict (telegram_chat_id) do update set
        name = excluded.name,
        telegram_username = excluded.telegram_username,
        desk_topic_id = excluded.desk_topic_id,
        owner_user_id = excluded.owner_user_id,
        updated_at = timezone('utc', now())
    returning *;
end;
$$;

create or replace function public.create_community_desk_listing(
    p_public_id text,
    p_telegram_chat_id bigint,
    p_desk_topic_id bigint,
    p_source_message_id bigint,
    p_owner_language text,
    p_kind text,
    p_description text,
    p_description_html text,
    p_deal_currency text,
    p_price numeric,
    p_item_fingerprint text
) returns setof public.desk_listings
language plpgsql
security definer
set search_path = public
as $$
declare
    v_community public.referral_communities%rowtype;
    v_username text;
begin
    select * into v_community
    from public.referral_communities
    where telegram_chat_id = p_telegram_chat_id
      and desk_topic_id = p_desk_topic_id
      and desk_enabled = true
    for update;

    if not found or v_community.owner_user_id is null then
        return;
    end if;

    perform pg_advisory_xact_lock(hashtextextended(p_item_fingerprint, 0));

    if exists (
        select 1 from public.desk_listings
        where source_type = 'community'
          and (
              (community_id = v_community.id and source_message_id = p_source_message_id)
              or (
                  item_fingerprint = p_item_fingerprint
                  and status in ('publishing', 'published')
              )
          )
    ) then
        return;
    end if;

    v_username := coalesce(
        nullif(v_community.telegram_username, ''),
        'community_' || v_community.id::text
    );

    return query
    insert into public.desk_listings(
        public_id,
        owner_id,
        owner_username,
        owner_language,
        kind,
        description,
        description_html,
        deal_currency,
        price,
        payment_currency,
        publication_fee,
        publication_fee_atomic,
        status,
        payment_deadline_at,
        source_type,
        community_id,
        source_chat_id,
        source_topic_id,
        source_message_id,
        item_fingerprint,
        community_name,
        community_username
    ) values (
        p_public_id,
        v_community.owner_user_id,
        v_username,
        p_owner_language,
        p_kind,
        p_description,
        p_description_html,
        p_deal_currency,
        p_price,
        'TON',
        0,
        0,
        'publishing',
        timezone('utc', now()),
        'community',
        v_community.id,
        p_telegram_chat_id,
        p_desk_topic_id,
        p_source_message_id,
        p_item_fingerprint,
        v_community.name,
        v_community.telegram_username
    )
    returning *;
end;
$$;

revoke all on function public.connect_community_desk(bigint,bigint,text,text,bigint)
    from public, anon, authenticated;
grant execute on function public.connect_community_desk(bigint,bigint,text,text,bigint)
    to service_role;
revoke all on function public.create_community_desk_listing(
    text,bigint,bigint,bigint,text,text,text,text,text,numeric,text
) from public, anon, authenticated;
grant execute on function public.create_community_desk_listing(
    text,bigint,bigint,bigint,text,text,text,text,text,numeric,text
) to service_role;

notify pgrst, 'reload schema';
commit;
