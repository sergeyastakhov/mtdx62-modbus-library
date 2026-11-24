"""How the sensor is configured: range, delays, sensitivity and bus settings.

Every field here is read-only. Writing the sensor's configuration is a separate
feature, so the library exposes no writable field at all.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer

from .const import (
    DISTANCE_SCALE,
    HOLDING_ACTIVE_REPORT,
    HOLDING_BAUDRATE,
    HOLDING_DEPARTURE_DELAY,
    HOLDING_DETECTION_DISTANCE,
    HOLDING_ENTRY_DELAY,
    HOLDING_ENTRY_INDENT,
    HOLDING_LIGHT_THRESHOLD,
    HOLDING_MAINTAIN_SENSITIVITY,
    HOLDING_PARITY,
    HOLDING_REPORT_INTERVAL,
    HOLDING_SHIELDING_DISTANCE,
    HOLDING_TRIGGER_SENSITIVITY,
    HOLDING_UNIT_ID,
    HUNDREDTHS_SCALE,
)


class Settings(Component):
    """The sensor's parameters, read from the holding registers on request."""

    detection_distance = gauge(HOLDING_DETECTION_DISTANCE, DISTANCE_SCALE, signed=False, unit="m")
    """Furthest distance the sensor reports a target at."""

    shielding_distance = gauge(HOLDING_SHIELDING_DISTANCE, DISTANCE_SCALE, signed=False, unit="m")
    """Nearest distance the sensor ignores, used to cut off reflections at the edge."""

    entry_delay = gauge(HOLDING_ENTRY_DELAY, HUNDREDTHS_SCALE, signed=False, unit="s")
    """Time a target must be present before the sensor reports it."""

    departure_delay = integer(HOLDING_DEPARTURE_DELAY, signed=False, unit="s")
    """Time without a target before the sensor reports the room as empty."""

    trigger_sensitivity = integer(HOLDING_TRIGGER_SENSITIVITY, signed=False)
    """Sensitivity for the first trigger, 1 to 9."""

    maintain_sensitivity = integer(HOLDING_MAINTAIN_SENSITIVITY, signed=False)
    """Sensitivity that keeps the target detected, 1 to 9."""

    entry_indent = gauge(HOLDING_ENTRY_INDENT, DISTANCE_SCALE, signed=False, unit="m")
    """How far inside the detection distance the first trigger happens."""

    unit_id = integer(HOLDING_UNIT_ID, signed=False)
    """Address of the sensor on the Modbus bus, 1 to 247."""

    baudrate = integer(HOLDING_BAUDRATE, signed=False, unit="baud")
    """Bus speed the sensor is configured for."""

    parity = integer(HOLDING_PARITY, signed=False)
    """Parity setting: 0 none, 1 odd, 2 even."""

    active_report = integer(HOLDING_ACTIVE_REPORT, signed=False)
    """Active reporting flag: 1 on, 2 off."""

    light_threshold = gauge(HOLDING_LIGHT_THRESHOLD, HUNDREDTHS_SCALE, signed=False, unit="lx")
    """Illuminance threshold for the sensor's own light-gated output; 0 disables it."""

    report_interval = integer(HOLDING_REPORT_INTERVAL, signed=False, unit="s")
    """Interval of the sensor's active reporting."""
