begin;

alter table users enable row level security;
alter table deals enable row level security;
alter table deal_payments enable row level security;
alter table collection_attempts enable row level security;
alter table payout_attempts enable row level security;
alter table referrals enable row level security;

revoke all on function claim_deal_payment(bigint, text, numeric, numeric, text, timestamptz) from public, anon, authenticated;
revoke all on function claim_deal_collection(bigint, text, text) from public, anon, authenticated;
revoke all on function save_prepared_collection(bigint, text, text, timestamptz) from public, anon, authenticated;
revoke all on function mark_collection_submitted(bigint) from public, anon, authenticated;
revoke all on function mark_collection_confirmed(bigint) from public, anon, authenticated;
revoke all on function mark_collection_bounced(bigint, text) from public, anon, authenticated;
revoke all on function mark_collection_failed(bigint, text) from public, anon, authenticated;
revoke all on function request_deal_release(bigint, bigint) from public, anon, authenticated;
revoke all on function claim_deal_buyer(text, bigint) from public, anon, authenticated;
revoke all on function assign_user_referrer(bigint, bigint) from public, anon, authenticated;
revoke all on function credit_referral_reward(bigint, bigint, text, numeric) from public, anon, authenticated;
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
grant execute on function claim_deal_collection(bigint, text, text) to service_role;
grant execute on function save_prepared_collection(bigint, text, text, timestamptz) to service_role;
grant execute on function mark_collection_submitted(bigint) to service_role;
grant execute on function mark_collection_confirmed(bigint) to service_role;
grant execute on function mark_collection_bounced(bigint, text) to service_role;
grant execute on function mark_collection_failed(bigint, text) to service_role;
grant execute on function request_deal_release(bigint, bigint) to service_role;
grant execute on function claim_deal_buyer(text, bigint) to service_role;
grant execute on function assign_user_referrer(bigint, bigint) to service_role;
grant execute on function credit_referral_reward(bigint, bigint, text, numeric) to service_role;
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
