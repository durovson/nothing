from app.database import SupabaseDatabase
from app.models.entities import DisputeTicket


class DisputeRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def open(
        self,
        deal_id: int,
        actor_id: int,
        description: str,
    ) -> DisputeTicket | None:
        response = await self._database.rpc(
            "open_deal_dispute",
            {
                "p_deal_id": deal_id,
                "p_actor_id": actor_id,
                "p_description": description,
            },
        )
        return DisputeTicket(**response.data[0]) if response.data else None
