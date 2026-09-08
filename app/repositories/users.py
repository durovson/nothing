from collections import OrderedDict
from time import monotonic
from typing import Unpack

from app.core.constants import USER_CACHE_MAX_ENTRIES, USER_CACHE_TTL_SECONDS
from app.core.enums import Language
from app.core.types import UserChanges
from app.database import SupabaseDatabase
from app.models.entities import User


class UserRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database
        self._cache: OrderedDict[int, tuple[float, User]] = OrderedDict()

    def _cached(self, telegram_id: int) -> User | None:
        item = self._cache.get(telegram_id)
        if item is None:
            return None
        cached_at, user = item
        if monotonic() - cached_at >= USER_CACHE_TTL_SECONDS:
            self._cache.pop(telegram_id, None)
            return None
        self._cache.move_to_end(telegram_id)
        return user

    def _remember(self, user: User) -> User:
        self._cache[user.telegram_id] = (monotonic(), user)
        self._cache.move_to_end(user.telegram_id)
        while len(self._cache) > USER_CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)
        return user

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
        return self._remember(User(**response.data[0]))

    async def get(self, telegram_id: int) -> User | None:
        cached = self._cached(telegram_id)
        if cached is not None:
            return cached
        response = await self._database.read(
            lambda: self._database.client.table("users")
            .select("*")
            .eq("telegram_id", telegram_id)
            .limit(1)
            .execute(),
            name="users:get-one",
        )
        return self._remember(User(**response.data[0])) if response.data else None

    async def get_many(self, telegram_ids: set[int]) -> dict[int, User]:
        if not telegram_ids:
            return {}
        users = {
            telegram_id: cached
            for telegram_id in telegram_ids
            if (cached := self._cached(telegram_id)) is not None
        }
        missing_ids = telegram_ids - users.keys()
        if not missing_ids:
            return users
        response = await self._database.read(
            lambda: self._database.client.table("users")
            .select("*")
            .in_("telegram_id", sorted(missing_ids))
            .limit(len(missing_ids))
            .execute(),
            name="users:get-many",
        )
        for item in response.data or []:
            user = self._remember(User(**item))
            users[user.telegram_id] = user
        return users

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
        return self._remember(User(**response.data[0]))

    async def list_ids(self, offset: int, limit: int) -> list[int]:
        response = await self._database.read(
            lambda: self._database.client.table("users")
            .select("telegram_id").order("telegram_id").range(offset, offset + limit - 1).execute()
        )
        return [int(item["telegram_id"]) for item in response.data]
