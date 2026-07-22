from app.core.enums import Language
from app.core.types import UserRepositoryProtocol
from app.models.entities import User


class UserService:
    def __init__(self, users: UserRepositoryProtocol):
        self._users = users

    async def ensure_user(
        self,
        telegram_id: int,
        username: str | None,
        default_language: Language,
    ) -> User:
        return await self._users.ensure_user(telegram_id, username, default_language)

    async def change_language(self, telegram_id: int, language: Language) -> User:
        return await self._users.update(telegram_id, language=language)

    async def get(self, telegram_id: int) -> User | None:
        return await self._users.get(telegram_id)

