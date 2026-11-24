"""The device object: one sensor reached through a ``ModbusUnit``."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from modbus_connection.model import Device, Raw, UpdateReport

from .readings import Readings
from .settings import Settings

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

READINGS = ("readings",)
SETTINGS = ("settings",)
ALL = (*READINGS, *SETTINGS)


class Mtdx62Device(Device):
    """An MTD062-MB or MTD262-MB presence sensor.

    The caller owns the connection and passes the unit; this object only reads
    registers. Measurements and parameters refresh on separate calls, because
    measurements are polled constantly and parameters only when diagnosing.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        """Wrap one unit of a Modbus link."""
        super().__init__(unit)
        self.readings = Readings(unit)
        self.settings = Settings(unit)

    async def async_update_readings(self) -> UpdateReport:
        """Refresh what the sensor measures."""
        return await self.async_poll(READINGS)

    async def async_update_settings(self) -> UpdateReport:
        """Refresh how the sensor is configured."""
        return await self.async_poll(SETTINGS)

    async def async_read_raw(self, names: Iterable[str] = ALL) -> Raw:
        """Read every register behind the named sub-systems, undecoded.

        This is what to attach to a bug report: raw words keyed by register
        space and address, so the reading can be replayed in a test.
        """
        return await super().async_read_raw(names)
