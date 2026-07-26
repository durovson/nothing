from app.database import SupabaseDatabase
from app.models.entities import BotSettings, Deal, DisputeTicket


class AdminRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def list_disputes(self, page: int, page_size: int) -> tuple[list[DisputeTicket], bool]:
        offset = max(0, page) * page_size
        response = await self._database.rpc(
            "list_admin_disputes",
            {"p_offset": offset, "p_limit": page_size + 1},
        )
        rows = [DisputeTicket(**item) for item in response.data]
        return rows[:page_size], len(rows) > page_size

    async def get_dispute(self, ticket_id: int) -> DisputeTicket | None:
        response = await self._database.read(
            lambda: self._database.client.table("dispute_tickets")
            .select("*").eq("id", ticket_id).limit(1).execute()
        )
        return DisputeTicket(**response.data[0]) if response.data else None

    async def resolve_release(self, deal_id: int, reason: str) -> Deal | None:
        response = await self._database.rpc(
            "resolve_dispute_release", {"p_deal_id": deal_id, "p_reason": reason}
        )
        return Deal(**response.data[0]) if response.data else None

    async def resolve_refund(self, deal_id: int, reason: str) -> Deal | None:
        response = await self._database.rpc(
            "resolve_dispute_refund", {"p_deal_id": deal_id, "p_reason": reason}
        )
        return Deal(**response.data[0]) if response.data else None

    async def get_settings(self) -> BotSettings:
        response = await self._database.read(
            lambda: self._database.client.table("bot_settings").select("*").eq("id", 1).single().execute()
        )
        return BotSettings(**response.data)

    async def set_maintenance(self, enabled: bool, message: str | None = None) -> BotSettings:
        changes: dict[str, object] = {"maintenance_enabled": enabled}
        if message:
            changes["maintenance_message"] = message.strip()[:1000]
        response = await self._database.run(
            lambda: self._database.client.table("bot_settings").update(changes).eq("id", 1).execute()
        )
        return BotSettings(**response.data[0])
