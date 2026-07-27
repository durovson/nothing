begin;

drop function if exists claim_deal_refund(bigint, text, numeric, text, text);

create or replace function mark_deal_delivered(
    p_deal_id bigint,
    p_seller_id bigint,
    p_inspection_deadline_at timestamptz
) returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update deals
    set status = 'delivered', delivered_at = timezone('utc', now()),
        inspection_deadline_at = p_inspection_deadline_at,
        updated_at = timezone('utc', now())
    where id = p_deal_id and creator_id = p_seller_id
      and status = 'delivery_pending'
      and delivery_deadline_at > timezone('utc', now())
    returning *;
end;
$$;

create or replace function open_deal_dispute(
    p_deal_id bigint,
    p_actor_id bigint,
    p_description text
) returns setof dispute_tickets
language plpgsql security definer set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_ticket dispute_tickets%rowtype;
begin
    if char_length(btrim(p_description)) not between 10 and 1000 then
        raise exception 'dispute description must contain 10 to 1000 characters';
    end if;
    select * into v_deal from deals where id = p_deal_id for update;
    if not found or p_actor_id not in (v_deal.creator_id, v_deal.buyer_id) then
        return;
    end if;
    if v_deal.status = 'delivered'
       and v_deal.inspection_deadline_at <= timezone('utc', now()) then
        return;
    end if;
    if v_deal.status not in ('delivery_pending', 'delivered') then
        return;
    end if;
    insert into dispute_tickets(deal_id, opened_by, description)
    values (p_deal_id, p_actor_id, btrim(p_description))
    on conflict (deal_id) where status = 'open' do nothing
    returning * into v_ticket;
    if v_ticket.id is null then return; end if;
    update deals set status = 'disputed', updated_at = timezone('utc', now())
    where id = p_deal_id;
    return next v_ticket;
end;
$$;

create or replace function request_expired_delivery_refund(p_deal_id bigint)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update deals as d
    set status = case
            when u.wallet_address is null then 'refund_awaiting_wallet'
            else 'refund_requested'
        end,
        resolution = 'refund', resolution_reason = 'Seller delivery deadline expired',
        updated_at = timezone('utc', now())
    from users as u
    where d.id = p_deal_id and d.buyer_id = u.telegram_id
      and d.status = 'delivery_pending'
      and d.delivery_deadline_at <= timezone('utc', now())
    returning d.*;
end;
$$;

create or replace function request_expired_inspection_release(p_deal_id bigint)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update deals
    set status = 'release_requested', resolution = 'auto_release',
        resolution_reason = 'Buyer inspection deadline expired',
        updated_at = timezone('utc', now())
    where id = p_deal_id and status = 'delivered'
      and inspection_deadline_at <= timezone('utc', now())
    returning *;
end;
$$;

create or replace function activate_refund_after_wallet(p_deal_id bigint)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update deals as d
    set status = 'refund_requested', updated_at = timezone('utc', now())
    from users as u
    where d.id = p_deal_id and d.buyer_id = u.telegram_id
      and d.status = 'refund_awaiting_wallet'
      and u.wallet_address is not null
    returning d.*;
end;
$$;

create or replace function claim_deal_refund(
    p_deal_id bigint,
    p_destination text,
    p_amount_atomic numeric,
    p_comment text,
    p_reason text,
    p_reward_destination text,
    p_reward_nominal_amount_atomic numeric,
    p_reward_comment text
) returns setof refund_attempts
language plpgsql security definer set search_path = public
as $$
declare
    v_deal deals%rowtype;
    v_attempt refund_attempts%rowtype;
begin
    if p_amount_atomic is null or p_amount_atomic <= 0 then
        raise exception 'refund amount must be positive';
    end if;
    if nullif(btrim(p_reward_destination), '') is null
       or p_reward_nominal_amount_atomic is null or p_reward_nominal_amount_atomic <= 0
       or char_length(btrim(p_reward_comment)) not between 1 and 120 then
        raise exception 'service reward data is invalid';
    end if;
    select * into v_deal from deals where id = p_deal_id for update;
    if not found or v_deal.status <> 'refund_requested' then return; end if;
    if exists (select 1 from refund_attempts where deal_id = p_deal_id) then return; end if;
    if exists (
        select 1 from referral_withdrawals
        where status in ('creating', 'prepared', 'submitted')
    ) then return; end if;
    insert into refund_attempts(
        deal_id, idempotency_key, status, destination, amount_atomic, comment, reason,
        reward_destination, reward_nominal_amount_atomic, reward_comment, currency
    ) values (
        p_deal_id, 'deal:' || p_deal_id::text || ':refund', 'creating',
        p_destination, p_amount_atomic, p_comment, p_reason,
        p_reward_destination, p_reward_nominal_amount_atomic, p_reward_comment, v_deal.currency
    ) returning * into v_attempt;
    update deals set status = 'refund_processing', updated_at = timezone('utc', now())
    where id = p_deal_id;
    return next v_attempt;
end;
$$;

create or replace function save_prepared_refund(
    p_attempt_id bigint, p_external_message_hash text, p_signed_boc text,
    p_valid_until timestamptz
) returns setof refund_attempts
language plpgsql security definer set search_path = public
as $$
begin
    return query update refund_attempts
    set status = 'prepared', external_message_hash = p_external_message_hash,
        signed_boc = p_signed_boc, valid_until = p_valid_until,
        updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'creating' returning *;
end;
$$;

create or replace function mark_refund_submitted(p_attempt_id bigint)
returns setof refund_attempts
language plpgsql security definer set search_path = public
as $$
declare v_attempt refund_attempts%rowtype;
begin
    select * into v_attempt from refund_attempts where id = p_attempt_id for update;
    if not found then return; end if;
    if v_attempt.status = 'prepared' then
        update refund_attempts set status = 'submitted',
            submitted_at = coalesce(submitted_at, timezone('utc', now())),
            updated_at = timezone('utc', now())
        where id = p_attempt_id returning * into v_attempt;
        update deals set status = 'refund_submitted', updated_at = timezone('utc', now())
        where id = v_attempt.deal_id and status = 'refund_processing';
    elsif v_attempt.status not in ('submitted', 'confirmed') then return;
    end if;
    return next v_attempt;
end;
$$;

create or replace function mark_refund_confirmed(p_attempt_id bigint)
returns setof deals
language plpgsql security definer set search_path = public
as $$
declare v_deal_id bigint;
begin
    update refund_attempts set status = 'confirmed', confirmed_at = timezone('utc', now()),
        last_checked_at = timezone('utc', now()), updated_at = timezone('utc', now())
    where id = p_attempt_id and status = 'submitted' returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query update deals set status = 'refunded', resolution = 'refund',
        failure_reason = null, updated_at = timezone('utc', now())
    where id = v_deal_id and status = 'refund_submitted' returning *;
end;
$$;

create or replace function mark_refund_bounced(p_attempt_id bigint, p_error text)
returns setof deals
language plpgsql security definer set search_path = public
as $$
declare v_deal_id bigint;
begin
    update refund_attempts set status = 'bounced', error = p_error,
        last_checked_at = timezone('utc', now()), updated_at = timezone('utc', now())
    where id = p_attempt_id and status in ('prepared', 'submitted')
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query update deals set status = 'refund_bounced', failure_reason = p_error,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status in ('refund_processing', 'refund_submitted') returning *;
end;
$$;

create or replace function mark_refund_failed(p_attempt_id bigint, p_error text)
returns setof deals
language plpgsql security definer set search_path = public
as $$
declare v_deal_id bigint;
begin
    update refund_attempts set status = 'failed', error = p_error,
        last_checked_at = timezone('utc', now()), updated_at = timezone('utc', now())
    where id = p_attempt_id and status in ('creating', 'prepared', 'submitted')
    returning deal_id into v_deal_id;
    if v_deal_id is null then return; end if;
    return query update deals set status = 'refund_failed', failure_reason = p_error,
        updated_at = timezone('utc', now())
    where id = v_deal_id and status in ('refund_processing', 'refund_submitted') returning *;
end;
$$;

create or replace function resolve_dispute_release(p_deal_id bigint, p_reason text)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    update dispute_tickets set status = 'resolved_release', resolution = 'release',
        resolution_reason = p_reason, updated_at = timezone('utc', now())
    where deal_id = p_deal_id and status = 'open';
    return query update deals set status = 'release_requested', resolution = 'release',
        resolution_reason = p_reason, updated_at = timezone('utc', now())
    where id = p_deal_id and status = 'disputed' returning *;
end;
$$;

create or replace function list_admin_disputes(p_offset integer, p_limit integer)
returns setof dispute_tickets
language sql security definer set search_path = public
as $$
    select * from dispute_tickets
    order by (status = 'open') desc, created_at desc, id desc
    offset greatest(p_offset, 0)
    limit least(greatest(p_limit, 1), 50);
$$;

create or replace function resolve_dispute_refund(p_deal_id bigint, p_reason text)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    update dispute_tickets set status = 'resolved_refund', resolution = 'refund',
        resolution_reason = p_reason, updated_at = timezone('utc', now())
    where deal_id = p_deal_id and status = 'open';
    return query update deals as d
    set status = case when u.wallet_address is null then 'refund_awaiting_wallet'
                      else 'refund_requested' end,
        resolution = 'refund', resolution_reason = p_reason,
        updated_at = timezone('utc', now())
    from users as u
    where d.id = p_deal_id and d.buyer_id = u.telegram_id
      and d.status = 'disputed' returning d.*;
end;
$$;

create or replace function mark_channel_access_granted(p_deal_id bigint)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update deals set
        channel_access_granted_at = coalesce(channel_access_granted_at, timezone('utc', now())),
        channel_access_error = null,
        updated_at = timezone('utc', now())
    where id = p_deal_id and deal_type = 'channel'
      and status = 'delivery_pending' and buyer_id is not null
    returning *;
end;
$$;

create or replace function request_channel_release_after_access(p_deal_id bigint)
returns setof deals
language plpgsql security definer set search_path = public
as $$
begin
    return query update deals set
        status = 'release_requested',
        updated_at = timezone('utc', now())
    where id = p_deal_id and deal_type = 'channel'
      and status = 'delivery_pending'
      and channel_access_granted_at is not null
      and buyer_id is not null
    returning *;
end;
$$;

commit;
