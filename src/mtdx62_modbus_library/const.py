"""Register addresses and value types of the MTD062-MB / MTD262-MB presence sensors."""

from __future__ import annotations

from enum import IntEnum

MANUFACTURER = "Zhejiang Oujue Electronic Technology"

# Input registers (function code 04). Addresses are zero-based; the PLC addressing
# in the vendor documentation starts these at 30001.
INPUT_PRESENCE = 0x0000
INPUT_ILLUMINANCE = 0x0001
INPUT_TARGET_DISTANCE = 0x0002
INPUT_STATUS = 0x0003
INPUT_APP_VERSION = 0x0004
INPUT_RADAR_VERSION = 0x0006

# Holding registers (function code 03). The vendor documentation starts these at 40001.
HOLDING_DETECTION_DISTANCE = 0x0000
HOLDING_SHIELDING_DISTANCE = 0x0001
HOLDING_ENTRY_DELAY = 0x0002
HOLDING_DEPARTURE_DELAY = 0x0003
HOLDING_TRIGGER_SENSITIVITY = 0x0004
HOLDING_MAINTAIN_SENSITIVITY = 0x0005
HOLDING_ENTRY_INDENT = 0x0006
HOLDING_UNIT_ID = 0x0007
HOLDING_BAUDRATE = 0x0008
HOLDING_PARITY = 0x0009
HOLDING_ACTIVE_REPORT = 0x000A
HOLDING_LIGHT_THRESHOLD = 0x000B
HOLDING_REPORT_INTERVAL = 0x000C

# The sensor reports distance in centimetres.
DISTANCE_SCALE = 0.01
# Delay and threshold registers carry hundredths of their unit.
HUNDREDTHS_SCALE = 0.01


class DeviceStatus(IntEnum):
    """Self-reported health of the sensor, from input register ``0x0003``.

    A running sensor reports ``OK``. ``SELF_CHECK_IN_PROGRESS`` is the transient
    state during power-up, and anything from ``SELF_TEST_FAILED`` upwards is a
    fault the sensor will not clear on its own.
    """

    SELF_CHECK_IN_PROGRESS = 0
    OK = 1
    SELF_TEST_FAILED = 2
    OTHER_FAULT = 3
    RADAR_FAULT = 4
    RS485_FAULT = 5
    RADAR_AND_RS485_FAULT = 6

    @property
    def is_fault(self) -> bool:
        """Whether the code means the sensor is broken rather than booting or fine."""
        return self.value >= DeviceStatus.SELF_TEST_FAILED
