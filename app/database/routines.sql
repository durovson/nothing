begin;

create or replace function claim_deal_buyer(p_public_id text, p_buyer_id bigint)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
begin
    select * into v_deal from deals where public_id = p_public_id for update;
    if not found or v_deal.status <> 'pending' or v_deal.creator_id = p_buyer_id then
        return;
    end if;
    if v_deal.buyer_id is not null and v_deal.buyer_id <> p_buyer_id then
        return;
    end if;
    if v_deal.buyer_id is null then
        update deals set buyer_id = p_buyer_id, updated_at = timezone('utc', now())
        where id = v_deal.id returning * into v_deal;
    end if;
    return next v_deal;
end;
$$;

create or replace function assign_user_referrer(
    p_referrer_id bigint,
    p_referred_id bigint
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
    v_current_referrer bigint;
begin
    if p_referrer_id = p_referred_id then
        return false;
    end if;
    if not exists (select 1 from users where telegram_id = p_referrer_id) then
        return false;
    end if;

    select referrer_id into v_current_referrer
    from users
    where telegram_id = p_referred_id
    for update;
    if not found or v_current_referrer is not null then
        return false;
    end if;

    update users set referrer_id = p_referrer_id where telegram_id = p_referred_id;
    insert into referrals(referrer_id, referred_id)
    values (p_referrer_id, p_referred_id)
    on conflict (referrer_id, referred_id) do nothing;
    return true;
end;
$$;

create or replace function credit_referral_reward(
    p_referrer_id bigint,
    p_referred_id bigint,
    p_currency text,
    p_amount numeric
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_amount is null or p_amount <= 0 then
        raise exception 'referral reward must be positive';
    end if;
    if p_currency = 'TON' then
        insert into referrals(referrer_id, referred_id, earned_ton)
        values (p_referrer_id, p_referred_id, p_amount)
        on conflict (referrer_id, referred_id)
        do update set earned_ton = referrals.earned_ton + excluded.earned_ton;
    elsif p_currency = 'USDT_TON' then
        insert into referrals(referrer_id, referred_id, earned_usdt)
        values (p_referrer_id, p_referred_id, p_amount)
        on conflict (referrer_id, referred_id)
        do update set earned_usdt = referrals.earned_usdt + excluded.earned_usdt;
    else
        raise exception 'unsupported referral currency: %', p_currency;
    end if;
end;
$$;

create or replace function claim_deal_payment(
    p_deal_id bigint,
    p_tx_hash text,
    p_tx_lt numeric,
    p_amount_atomic numeric,
    p_sender text,
    p_observed_at timestamptz
) returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_payment_id bigint;
begin
    select * into v_deal from deals where id = p_deal_id for update;
    if not found or v_deal.status <> 'pending' then
        return;
    end if;

    insert into deal_payments(deal_id, tx_hash, tx_lt, amount_atomic, sender, observed_at)
    values (p_deal_id, p_tx_hash, p_tx_lt, p_amount_atomic, p_sender, p_observed_at)
    on conflict do nothing
    returning id into v_payment_id;
    if v_payment_id is null then
        return;
    end if;

    update deals
    set status = 'paid', paid_tx_hash = p_tx_hash, paid_tx_lt = p_tx_lt,
        paid_amount_atomic = p_amount_atomic, payment_sender = p_sender,
        paid_at = p_observed_at, updated_at = timezone('utc', now())
    where id = p_deal_id
    returning * into v_deal;
    return next v_deal;
end;
$$;

create or replace function claim_deal_payout(
    p_deal_id bigint,
    p_destination text,
    p_amount_atomic numeric,
    p_comment text
) returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_attempt payout_attempts%rowtype;
begin
    select * into v_deal from deals where id = p_deal_id for update;
    if not found or v_deal.status <> 'paid' then
        return;
    end if;
    if exists (select 1 from payout_attempts where deal_id = p_deal_id) then
        return;
    end if;

    insert into payout_attempts(
        deal_id, idempotency_key, status, destination, amount_atomic, comment
    ) values (
        p_deal_id, 'deal:' || p_deal_id::text || ':seller', 'creating',
        p_destination, p_amount_atomic, p_comment
    ) returning * into v_attempt;

    update deals
    set status = 'payout_processing', updated_at = timezone('utc', now())
    where id = p_deal_id;
    return next v_attempt;
end;
$$;

create or replace function claim_deal_batch_payout(
    p_deal_id bigint,
    p_destination text,
    p_amount_atomic numeric,
    p_comment text,
    p_reward_destination text,
    p_reward_nominal_amount_atomic numeric,
    p_reward_comment text
) returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_attempt payout_attempts%rowtype;
begin
    if p_amount_atomic is null or p_amount_atomic <= 0 then
        raise exception 'seller payout must be positive';
    end if;
    if p_reward_nominal_amount_atomic is null or p_reward_nominal_amount_atomic <= 0 then
        raise exception 'service reward must be positive';
    end if;
    if nullif(btrim(p_reward_destination), '') is null then
        raise exception 'service reward destination is required';
    end if;
    if p_reward_comment is null
       or char_length(btrim(p_reward_comment)) not between 1 and 120 then
        raise exception 'service reward comment is invalid';
    end if;

    select * into v_deal from deals where id = p_deal_id for update;
    if not found or v_deal.status <> 'paid' then
        return;
    end if;
    if exists (select 1 from payout_attempts where deal_id = p_deal_id) then
        return;
    end if;

    insert into payout_attempts(
        deal_id,
        idempotency_key,
        status,
        destination,
        amount_atomic,
        comment,
        reward_destination,
        reward_nominal_amount_atomic,
        reward_comment
    ) values (
        p_deal_id,
        'deal:' || p_deal_id::text || ':batch',
        'creating',
        p_destination,
        p_amount_atomic,
        p_comment,
        p_reward_destination,
        p_reward_nominal_amount_atomic,
        p_reward_comment
    ) returning * into v_attempt;

    update deals
    set status = 'payout_processing', updated_at = timezone('utc', now())
    where id = p_deal_id;
    return next v_attempt;
end;
$$;

create or replace function save_prepared_payout(
    p_attempt_id bigint,
    p_external_message_hash text,
    p_signed_boc text,
    p_valid_until timestamptz
) returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
begin
    return query
    update payout_attempts
    set status = 'prepared', external_message_hash = p_external_message_hash,
        signed_boc = p_signed_boc, valid_until = p_valid_until,
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'creating'
    returning *;
end;
$$;

create or replace function mark_payout_submitted(p_attempt_id bigint)
returns setof payout_attempts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
    v_attempt payout_attempts%rowtype;
begin
    select * into v_attempt
    from payout_attempts
    where id = p_attempt_id
    for update;
    if not found then
        return;
    end if;

    if v_attempt.status = 'prepared' then
        update payout_attempts
        set status = 'submitted', submitted_at = coalesce(submitted_at, timezone('utc', now())),
            updated_at = timezone('utc', now())
        where id = p_attempt_id
        returning * into v_attempt;

        v_deal_id := v_attempt.deal_id;
        update deals set status = 'payout_submitted', updated_at = timezone('utc', now())
        where id = v_deal_id and status = 'payout_processing';
    elsif v_attempt.status not in ('submitted', 'confirmed') then
        return;
    end if;

    return next v_attempt;
end;
$$;

create or replace function mark_payout_confirmed(p_attempt_id bigint)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'confirmed', confirmed_at = timezone('utc', now()),
        last_checked_at = timezone('utc', now()), updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'submitted'
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query
    update deals set status = 'completed', failure_reason = null,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status = 'payout_submitted'
    returning *;
end;
$$;

create or replace function mark_payout_bounced(p_attempt_id bigint, p_error text)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'bounced', error = p_error, last_checked_at = timezone('utc', now()),
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status in ('prepared', 'submitted')
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query
    update deals set status = 'payout_bounced', failure_reason = p_error,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status in ('payout_processing', 'payout_submitted')
    returning *;
end;
$$;

create or replace function mark_payout_failed(p_attempt_id bigint, p_error text)
returns setof deals
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deal_id bigint;
begin
    update payout_attempts
    set status = 'failed', error = p_error, last_checked_at = timezone('utc', now()),
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status in ('creating', 'prepared', 'submitted')
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query
    update deals set status = 'payout_failed', failure_reason = p_error,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status in ('payout_processing', 'payout_submitted')
    returning *;
end;
$$;

create or replace function purge_expired_unsuccessful_deals(p_retention_days integer)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
    v_deleted bigint;
begin
    if p_retention_days is null or p_retention_days < 1 or p_retention_days > 30 then
        raise exception 'retention must be between 1 and 30 days';
    end if;

    delete from deals
    where status in ('cancelled', 'creation_failed', 'payout_failed', 'payout_bounced')
      and updated_at < timezone('utc', now()) - make_interval(days => p_retention_days);

    get diagnostics v_deleted = row_count;
    return v_deleted;
end;
$$;

alter table users enable row level security;
alter table deals enable row level security;
alter table deal_payments enable row level security;
alter table payout_attempts enable row level security;
alter table referrals enable row level security;

revoke all on function claim_deal_payment(bigint, text, numeric, numeric, text, timestamptz) from public, anon, authenticated;
revoke all on function claim_deal_buyer(text, bigint) from public, anon, authenticated;
revoke all on function assign_user_referrer(bigint, bigint) from public, anon, authenticated;
revoke all on function credit_referral_reward(bigint, bigint, text, numeric) from public, anon, authenticated;
revoke all on function claim_deal_payout(bigint, text, numeric, text) from public, anon, authenticated;
revoke all on function claim_deal_batch_payout(bigint, text, numeric, text, text, numeric, text)
    from public, anon, authenticated;
revoke all on function save_prepared_payout(bigint, text, text, timestamptz) from public, anon, authenticated;
revoke all on function mark_payout_submitted(bigint) from public, anon, authenticated;
revoke all on function mark_payout_confirmed(bigint) from public, anon, authenticated;
revoke all on function mark_payout_bounced(bigint, text) from public, anon, authenticated;
revoke all on function mark_payout_failed(bigint, text) from public, anon, authenticated;
revoke all on function purge_expired_unsuccessful_deals(integer) from public, anon, authenticated;
revoke all on function assign_deal_wallet_identity() from public, anon, authenticated;

grant execute on function claim_deal_payment(bigint, text, numeric, numeric, text, timestamptz) to service_role;
grant execute on function claim_deal_buyer(text, bigint) to service_role;
grant execute on function assign_user_referrer(bigint, bigint) to service_role;
grant execute on function credit_referral_reward(bigint, bigint, text, numeric) to service_role;
revoke execute on function claim_deal_payout(bigint, text, numeric, text) from service_role;
grant execute on function claim_deal_batch_payout(bigint, text, numeric, text, text, numeric, text)
    to service_role;
grant execute on function save_prepared_payout(bigint, text, text, timestamptz) to service_role;
grant execute on function mark_payout_submitted(bigint) to service_role;
grant execute on function mark_payout_confirmed(bigint) to service_role;
grant execute on function mark_payout_bounced(bigint, text) to service_role;
grant execute on function mark_payout_failed(bigint, text) to service_role;
grant execute on function purge_expired_unsuccessful_deals(integer) to service_role;
grant usage, select on sequence deal_subwallet_id_seq to service_role;
grant usage, select on sequence deal_wallet_v5_subwallet_seq to service_role;

commit;
