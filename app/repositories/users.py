from typing import Unpack

from app.core.enums import Language
from app.core.types import UserChanges
from app.database import SupabaseDatabase
from app.models.entities import User


class UserRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def ensure_user(
        self,
        telegram_id: int,
        username: str | None,
        default_language: Language,
    ) -> User:
        user = await self.get(telegram_id)
        if user:
            if username and user.username != username:
                return await self.update(telegram_id, username=username)
            return user

        response = await self._database.run(
            lambda: self._database.client.table("users")
            .insert(
                {
                    "telegram_id": telegram_id,
                    "username": username,
                    "language": default_language.value,
                }
            )
            .execute()
        )
        return User(**response.data[0])

    async def get(self, telegram_id: int) -> User | None:
        response = await self._database.run(
            lambda: self._database.client.table("users")
            .select("*")
            .eq("telegram_id", telegram_id)
            .limit(1)
            .execute()
        )
        return User(**response.data[0]) if response.data else None

    async def update(self, telegram_id: int, **changes: Unpack[UserChanges]) -> User:
        serialized = {
            key: value.value if isinstance(value, Language) else value
            for key, value in changes.items()
        }
        response = await self._database.run(
            lambda: self._database.client.table("users")
            .update(serialized)
            .eq("telegram_id", telegram_id)
            .execute()
        )
        return User(**response.data[0])

