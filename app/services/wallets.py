from app.core.types import TonGatewayProtocol, UserRepositoryProtocol
from app.models.entities import User


class WalletService:
    def __init__(self, users: UserRepositoryProtocol, ton: TonGatewayProtocol):
        self._users = users
        self._ton = ton

    async def save(self, telegram_id: int, raw_address: str) -> User:
        normalized = self._ton.normalize_address(raw_address.strip())
        return await self._users.update(telegram_id, wallet_address=normalized)

    async def delete(self, telegram_id: int) -> User:
        return await self._users.update(telegram_id, wallet_address=None)

