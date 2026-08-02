from app.core.enums import SystemMode
from app.database import SupabaseDatabase
from app.models.entities import SystemSetting


class SystemSettingsRepository:
    def __init__(self, database: SupabaseDatabase):
        self._database = database

    async def get_mode(self) -> SystemSetting:
        response = await self._database.read(
            lambda: self._database.client.table("system_settings")
            .select("*").eq("key", "system_mode").single().execute(),
            name="system-settings:get-mode",
        )
        return SystemSetting(**response.data)

    async def set_mode(
        self,
        mode: SystemMode,
        reason: str,
        *,
        updated_by: int | None,
        automatic: bool,
    ) -> SystemSetting:
        response = await self._database.rpc(
            "set_system_mode",
            {
                "p_mode": mode.value,
                "p_reason": reason[:1000],
                "p_updated_by": updated_by,
                "p_automatic": automatic,
            },
        )
        return SystemSetting(**response.data[0])
