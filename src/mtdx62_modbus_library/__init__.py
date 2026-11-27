"""Read and configure the MTD062-MB and MTD262-MB Modbus presence sensors."""

from __future__ import annotations

from .const import DeviceStatus as DeviceStatus
from .device import ALL as ALL
from .device import READINGS as READINGS
from .device import SETTINGS as SETTINGS
from .device import Mtdx62Device as Mtdx62Device
from .errors import Mtdx62Error as Mtdx62Error
from .errors import WriteVerificationError as WriteVerificationError
from .readings import Readings as Readings
from .settings import Settings as Settings
from .settings import SettingSpec as SettingSpec

__version__ = "0.5.0"

__all__ = [
    "ALL",
    "READINGS",
    "SETTINGS",
    "DeviceStatus",
    "Mtdx62Device",
    "Mtdx62Error",
    "Readings",
    "SettingSpec",
    "Settings",
    "WriteVerificationError",
    "__version__",
]
