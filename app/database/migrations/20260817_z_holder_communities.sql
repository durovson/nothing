begin;

create table if not exists public.referral_communities (
    id bigint generated always as identity primary key,
    name text not null check (char_length(name) between 1 and 120),
    telegram_chat_id bigint not null unique,
    collection_address text,
    holder_share numeric(5, 4) not null default 0.30
        check (holder_share > 0 and holder_share <= 1),
    owner_user_id bigint references public.users(telegram_id) on delete set null,
    enabled boolean not null default true,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.referral_community_memberships (
    community_id bigint not null references public.referral_communities(id) on delete cascade,
    telegram_id bigint not null,
    status text not null check (status in ('active', 'inactive')),
    telegram_status text not null,
    joined_at timestamptz,
    left_at timestamptz,
    verified_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (community_id, telegram_id)
);

create index if not exists referral_community_memberships_active_user_idx
    on public.referral_community_memberships(telegram_id, community_id)
    where status = 'active';

create or replace function public.get_referral_profiles_with_entitlements(
    p_user_ids bigint[]
) returns table(
    user_id bigint,
    level text,
    ton_volume numeric,
    holder_community_id bigint,
    holder_community_name text,
    holder_share numeric
)
language sql
stable
security definer
set search_path = public
as $$
    select
        requested.user_id,
        coalesce(profile.level, 'level_1') as level,
        coalesce(profile.ton_volume, 0) as ton_volume,
        holder.community_id as holder_community_id,
        holder.community_name as holder_community_name,
        holder.holder_share
    from unnest(p_user_ids) as requested(user_id)
    left join public.referral_profiles profile on profile.user_id = requested.user_id
    left join lateral (
        select
            community.id as community_id,
            community.name as community_name,
            community.holder_share
        from public.referral_community_memberships membership
        join public.referral_communities community
          on community.id = membership.community_id
         and community.enabled = true
        where membership.telegram_id = requested.user_id
          and membership.status = 'active'
        order by community.holder_share desc, community.id asc
        limit 1
    ) holder on true;
$$;

create or replace function public.sync_referral_community_membership(
    p_telegram_chat_id bigint,
    p_telegram_id bigint,
    p_telegram_status text,
    p_active boolean
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
    v_community_id bigint;
    v_now timestamptz := timezone('utc', now());
begin
    select id into v_community_id
    from public.referral_communities
    where telegram_chat_id = p_telegram_chat_id and enabled = true;

    if v_community_id is null then
        return false;
    end if;

    insert into public.referral_community_memberships(
        community_id, telegram_id, status, telegram_status,
        joined_at, left_at, verified_at, updated_at
    ) values (
        v_community_id,
        p_telegram_id,
        case when p_active then 'active' else 'inactive' end,
        p_telegram_status,
        case when p_active then v_now else null end,
        case when p_active then null else v_now end,
        v_now,
        v_now
    )
    on conflict (community_id, telegram_id) do update set
        status = excluded.status,
        telegram_status = excluded.telegram_status,
        joined_at = case
            when excluded.status = 'active'
                 and public.referral_community_memberships.status <> 'active'
                then v_now
            else public.referral_community_memberships.joined_at
        end,
        left_at = case
            when excluded.status = 'inactive' then v_now
            else null
        end,
        verified_at = v_now,
        updated_at = v_now;

    return true;
end;
$$;

alter table public.referral_rewards
    add column if not exists commission_share numeric(5, 4) not null default 0.10
        check (commission_share > 0 and commission_share <= 1),
    add column if not exists reward_source text not null default 'level'
        check (reward_source in ('level', 'holder', 'special')),
    add column if not exists community_id bigint
        references public.referral_communities(id) on delete set null;

create or replace function public.snapshot_referral_reward_decision()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_share numeric(5, 4);
    v_source text;
    v_community_id bigint;
begin
    select x.commission_share, x.reward_source, x.community_id
    into v_share, v_source, v_community_id
    from public.financial_operations operation
    cross join lateral jsonb_to_recordset(
        coalesce(operation.metadata->'referral_allocations', '[]'::jsonb)
    ) as x(
        referrer_id bigint,
        referred_id bigint,
        amount numeric,
        commission_share numeric,
        reward_source text,
        community_id bigint
    )
    where operation.deal_id = new.deal_id
      and operation.flow = 'payout'
      and operation.type = 'seller_transfer'
      and x.referrer_id = new.referrer_id
      and x.referred_id = new.referred_id
    limit 1;

    if v_share is not null then
        new.commission_share := v_share;
        new.reward_source := coalesce(v_source, 'level');
        new.community_id := v_community_id;
    end if;
    return new;
end;
$$;

drop trigger if exists referral_rewards_snapshot_decision on public.referral_rewards;
create trigger referral_rewards_snapshot_decision
before insert on public.referral_rewards
for each row execute function public.snapshot_referral_reward_decision();

alter table public.referral_communities enable row level security;
alter table public.referral_community_memberships enable row level security;
revoke all on table public.referral_communities from public, anon, authenticated;
revoke all on table public.referral_community_memberships from public, anon, authenticated;
grant select, insert, update, delete on table public.referral_communities to service_role;
grant select, insert, update, delete on table public.referral_community_memberships to service_role;
grant usage, select on sequence public.referral_communities_id_seq to service_role;
revoke all on function public.sync_referral_community_membership(bigint, bigint, text, boolean)
    from public, anon, authenticated;
grant execute on function public.sync_referral_community_membership(bigint, bigint, text, boolean)
    to service_role;
revoke all on function public.get_referral_profiles_with_entitlements(bigint[])
    from public, anon, authenticated;
grant execute on function public.get_referral_profiles_with_entitlements(bigint[])
    to service_role;

notify pgrst, 'reload schema';
commit;
