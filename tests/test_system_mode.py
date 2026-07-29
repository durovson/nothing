import unittest
from datetime import UTC, datetime, timedelta

from app.core.enums import SystemMode
from app.models.entities import SystemSetting
from app.services.system_mode import SystemModeService


class SystemModeTests(unittest.IsolatedAsyncioTestCase):
    def service(self, mode: SystemMode) -> SystemModeService:
        service = object.__new__(SystemModeService)
        service._local_read_only = False
        service._cached = SystemSetting(key="system_mode", value=mode.value)
        service._cache_until = datetime.now(UTC) + timedelta(minutes=1)
        return service

    async def test_read_only_keeps_on_chain_recovery_visible(self) -> None:
        self.assertTrue(await self.service(SystemMode.READ_ONLY).accepts_deposits())

    async def test_manual_emergency_stops_deposit_collection(self) -> None:
        self.assertFalse(await self.service(SystemMode.EMERGENCY).accepts_deposits())


if __name__ == "__main__":
    unittest.main()
