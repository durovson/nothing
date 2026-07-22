import asyncio
from collections.abc import Callable
from typing import TypeVar

from supabase import Client, create_client

from app.config import Settings

ResultT = TypeVar("ResultT")


class SupabaseDatabase:
    """Async boundary around the synchronous Supabase client."""

    def __init__(self, settings: Settings):
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    async def run(self, operation: Callable[[], ResultT]) -> ResultT:
        return await asyncio.to_thread(operation)

    async def rpc(self, name: str, params: dict[str, object]):
        return await self.run(lambda: self.client.rpc(name, params).execute())

