from aiogram import Router

from app.handlers import admin, deal_creation, deal_manage, desk, info, referral_communities, settings, start, wallet


def create_router() -> Router:
    router = Router(name="application")
    router.include_routers(
        start.router,
        admin.router,
        wallet.router,
        info.router,
        deal_creation.router,
        deal_manage.router,
        desk.router,
        referral_communities.router,
        settings.router,
    )
    return router


__all__ = ["create_router"]
