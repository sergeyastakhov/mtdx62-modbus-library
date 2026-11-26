"""What the sensor measures: presence, illuminance, distance, health and versions."""

from __future__ import annotations

from modbus_connection.model import (
    Component,
    RegisterSpace,
    boolean,
    gauge,
    raw_register,
    uint32,
)

from .const import (
    DISTANCE_SCALE,
    INPUT_APP_VERSION,
    INPUT_ILLUMINANCE,
    INPUT_PRESENCE,
    INPUT_RADAR_VERSION,
    INPUT_STATUS,
    INPUT_TARGET_DISTANCE,
    TENTHS_SCALE,
    DeviceStatus,
)


def _format_version(value: int | None) -> str | None:
    """Turn the packed version word into ``major.minor.patch``.

    The sensor packs the three parts as the low three bytes of the register pair:
    ``0x00010203`` is version 1.2.3 and ``0x00000102`` is 0.1.2.
    """
    if value is None:
        return None
    return f"{(value >> 16) & 0xFF}.{(value >> 8) & 0xFF}.{value & 0xFF}"


class Readings(Component):
    """The sensor's measurements, read from the input registers in one block."""

    register_space: RegisterSpace = "input"

    presence = boolean(INPUT_PRESENCE)
    """Whether a person is detected, including someone sitting still."""

    illuminance = gauge(INPUT_ILLUMINANCE, TENTHS_SCALE, signed=False, unit="lx")
    """Ambient illuminance as the sensor sees it, in lux with a tenth of a lux."""

    distance = gauge(INPUT_TARGET_DISTANCE, DISTANCE_SCALE, signed=False, unit="m")
    """Distance to the detected target in metres, with a centimetre resolution."""

    status_code = raw_register(INPUT_STATUS)
    """Raw health code; see :class:`~mtdx62.const.DeviceStatus`."""

    app_version_raw = uint32(INPUT_APP_VERSION)
    """Application firmware version as the packed register pair."""

    radar_version_raw = uint32(INPUT_RADAR_VERSION)
    """Radar module firmware version as the packed register pair."""

    @property
    def status(self) -> DeviceStatus | None:
        """Health code as an enum, or ``None`` before the first read or for an unknown code."""
        code = self.status_code
        if code is None:
            return None
        try:
            return DeviceStatus(code)
        except ValueError:
            return None

    @property
    def app_version(self) -> str | None:
        """Application firmware version as ``major.minor.patch``."""
        return _format_version(self.app_version_raw)

    @property
    def radar_version(self) -> str | None:
        """Radar module firmware version as ``major.minor.patch``."""
        return _format_version(self.radar_version_raw)
