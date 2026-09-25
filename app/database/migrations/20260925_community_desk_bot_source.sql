begin;

-- Telegram Bot-to-Bot delivery exposes the real sender in Message.from.
-- Keep the allow-listed bot on the existing community record so similarly
-- formatted messages from people or unrelated bots cannot reach GRNT Desk.
alter table public.referral_communities
    add column if not exists desk_source_bot_id bigint,
    add column if not exists desk_source_bot_username text;

create index if not exists referral_communities_desk_source_bot_idx
    on public.referral_communities(telegram_chat_id, desk_topic_id, desk_source_bot_id)
    where desk_enabled = true;

notify pgrst, 'reload schema';
commit;
