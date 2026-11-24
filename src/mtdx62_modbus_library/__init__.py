"""Read the MTD062-MB and MTD262-MB Modbus presence sensors."""

from __future__ import annotations

from .const import DeviceStatus as DeviceStatus
from .device import ALL as ALL
from .device import READINGS as READINGS
from .device import SETTINGS as SETTINGS
from .device import Mtdx62Device as Mtdx62Device
from .readings import Readings as Readings
from .settings import Settings as Settings

__version__ = "0.3.0"

__all__ = [
    "ALL",
    "READINGS",
    "SETTINGS",
    "DeviceStatus",
    "Mtdx62Device",
    "Readings",
    "Settings",
    "__version__",
]
