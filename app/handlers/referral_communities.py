from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import ChatMember, ChatMemberUpdated

from app.services.referrals import ReferralService

logger = logging.getLogger(__name__)
router = Router(name="referral_communities")


def _membership_state(member: ChatMember) -> tuple[str, bool]:
    status = member.status.value
    active = status in {"creator", "administrator", "member"}
    if status == "restricted":
        active = bool(getattr(member, "is_member", False))
    return status, active


async def sync_user_community_memberships(
    bot: Bot,
    referral_service: ReferralService,
    telegram_id: int,
) -> None:
    """Refresh one user without attempting to enumerate the private chat."""
    for community in await referral_service.enabled_communities():
        try:
            member = await bot.get_chat_member(community.telegram_chat_id, telegram_id)
            status, active = _membership_state(member)
            await referral_service.sync_community_membership(
                community.telegram_chat_id,
                telegram_id,
                status,
                active,
            )
        except Exception:
            # A Telegram outage or lost bot permission must not revoke a cached
            # Holder entitlement. The next event or profile visit will retry.
            logger.warning(
                "Could not refresh referral community membership community=%s user=%s",
                community.id,
                telegram_id,
                exc_info=True,
            )


@router.chat_member()
async def community_membership_updated(
    event: ChatMemberUpdated,
    referral_service: ReferralService,
) -> None:
    target = event.new_chat_member.user
    if target.is_bot:
        return
    status, active = _membership_state(event.new_chat_member)
    try:
        await referral_service.sync_community_membership(
            event.chat.id,
            target.id,
            status,
            active,
        )
    except Exception:
        # Opening the referral screen later performs a targeted self-heal.
        logger.warning(
            "Could not persist referral community event chat=%s user=%s status=%s",
            event.chat.id,
            target.id,
            status,
            exc_info=True,
        )
