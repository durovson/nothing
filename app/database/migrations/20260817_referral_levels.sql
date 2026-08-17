begin;

create table if not exists public.referral_profiles (
    user_id bigint primary key references public.users(telegram_id) on delete restrict,
    level text not null default 'level_1'
        check (level in ('level_1', 'level_2', 'level_3', 'special')),
    ton_volume numeric(36, 9) not null default 0 check (ton_volume >= 0),
    updated_at timestamptz not null default timezone('utc', now())
);

-- Keep a profile for every referrer so that an administrator can switch the
-- level to `special` directly in the Table Editor before the first reward.
insert into public.referral_profiles(user_id)
select distinct referrer_id from public.referrals
on conflict (user_id) do nothing;

create or replace function public.ensure_referral_profile_after_relation()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.referral_profiles(user_id)
    values (new.referrer_id)
    on conflict (user_id) do nothing;
    return new;
end;
$$;

drop trigger if exists referrals_ensure_profile on public.referrals;
create trigger referrals_ensure_profile
after insert on public.referrals
for each row execute function public.ensure_referral_profile_after_relation();

-- Backfill confirmed historical referral deal volume. A deal is counted once
-- for each referred participant represented by a reward row.
insert into public.referral_profiles(user_id, level, ton_volume)
select
    r.referrer_id,
    case
        when coalesce(sum(d.amount) filter (where d.currency = 'TON'), 0) >= 1000 then 'level_3'
        when coalesce(sum(d.amount) filter (where d.currency = 'TON'), 0) >= 500 then 'level_2'
        else 'level_1'
    end,
    coalesce(sum(d.amount) filter (where d.currency = 'TON'), 0)
from public.referral_rewards r
join public.deals d on d.id = r.deal_id
group by r.referrer_id
on conflict (user_id) do update set
    ton_volume = excluded.ton_volume,
    level = case
        when public.referral_profiles.level = 'special' then 'special'
        else excluded.level
    end,
    updated_at = timezone('utc', now());

create or replace function public.update_referral_profile_after_reward()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_ton_volume numeric(36, 9) := 0;
begin
    select case when currency = 'TON' then amount else 0 end
    into v_ton_volume
    from public.deals
    where id = new.deal_id;

    insert into public.referral_profiles(user_id, level, ton_volume)
    values (
        new.referrer_id,
        case
            when v_ton_volume >= 1000 then 'level_3'
            when v_ton_volume >= 500 then 'level_2'
            else 'level_1'
        end,
        v_ton_volume
    )
    on conflict (user_id) do update set
        ton_volume = public.referral_profiles.ton_volume + excluded.ton_volume,
        level = case
            when public.referral_profiles.level = 'special' then 'special'
            when public.referral_profiles.ton_volume + excluded.ton_volume >= 1000 then 'level_3'
            when public.referral_profiles.ton_volume + excluded.ton_volume >= 500 then 'level_2'
            else 'level_1'
        end,
        updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists referral_rewards_update_profile on public.referral_rewards;
create trigger referral_rewards_update_profile
after insert on public.referral_rewards
for each row execute function public.update_referral_profile_after_reward();

alter table public.referral_profiles enable row level security;
revoke all on table public.referral_profiles from public, anon, authenticated;
grant select, insert, update on table public.referral_profiles to service_role;

notify pgrst, 'reload schema';
commit;
