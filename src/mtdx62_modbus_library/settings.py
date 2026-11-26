"""How the sensor is configured: range, delays, sensitivity and bus settings.

Parameters are read from the holding registers and, for everything the vendor
register map describes, can be written back. Writing is a tool, not a policy: the
library checks the value against the register map and confirms it by reading, but
it does not inspect the device's health, does not change the unit's own link
parameters and does not know whether a caller can still reach the device after
the bus address or the baud rate changed. Those decisions belong to the caller.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import Any

from modbus_connection.model import Component, WriteValidator, gauge, integer

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
    TENTHS_SCALE,
)
from .errors import WriteVerificationError

# The sensor shows the previous register value for up to half a second after a
# write, so a confirmation read taken immediately can see the old number. Retry
# until the value appears rather than reporting a failure that is not there.
CONFIRM_DEADLINE = 1.0
CONFIRM_PAUSE = 0.15


def _digits(step: float) -> int:
    """How many decimal places the step grants."""
    text = f"{step:f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """One writable parameter: what it is called, where it lives and its limits.

    A caller builds number and select entities from this instead of repeating
    the register map: the limits and the units stay in one place.
    """

    name: str
    address: int
    minimum: float
    maximum: float
    step: float
    unit: str | None
    raw_minimum: int
    raw_maximum: int
    integer: bool

    def coerce(self, value: Any) -> float | int:
        """Return the value snapped to the step, or raise ``ValueError``.

        Nothing is sent to the bus before this returns: a value outside the
        register map must not reach the device even as an attempt.
        """
        if isinstance(value, bool) or not isinstance(value, int | float | str):
            raise ValueError(f"{self.name} takes a number, not {value!r}")
        try:
            number = float(value)
        except ValueError as err:
            raise ValueError(f"{self.name} takes a number, not {value!r}") from err
        if not math.isfinite(number):
            raise ValueError(f"{self.name} takes a finite number, not {value!r}")
        number = round(number, _digits(self.step))
        if not self.minimum <= number <= self.maximum:
            raise ValueError(
                f"{self.name} must be between {self.minimum} and {self.maximum}"
                f" {self.unit or ''}".rstrip()
                + f", not {value!r}"
            )
        return int(number) if self.integer else number

    def matches(self, expected: float | int, stored: Any) -> bool:
        """Whether the value read back is the value that was written."""
        if stored is None:
            return False
        return abs(float(stored) - float(expected)) <= self.step / 2


_SPECS: dict[str, SettingSpec] = {
    spec.name: spec
    for spec in (
        SettingSpec(
            "detection_distance",
            HOLDING_DETECTION_DISTANCE,
            100 * DISTANCE_SCALE,
            1000 * DISTANCE_SCALE,
            DISTANCE_SCALE,
            "m",
            100,
            1000,
            False,
        ),
        SettingSpec(
            "shielding_distance",
            HOLDING_SHIELDING_DISTANCE,
            30 * DISTANCE_SCALE,
            1000 * DISTANCE_SCALE,
            DISTANCE_SCALE,
            "m",
            30,
            1000,
            False,
        ),
        SettingSpec(
            "entry_delay",
            HOLDING_ENTRY_DELAY,
            0.0,
            500 * HUNDREDTHS_SCALE,
            HUNDREDTHS_SCALE,
            "s",
            0,
            500,
            False,
        ),
        SettingSpec("departure_delay", HOLDING_DEPARTURE_DELAY, 5, 1500, 1, "s", 5, 1500, True),
        SettingSpec("trigger_sensitivity", HOLDING_TRIGGER_SENSITIVITY, 1, 9, 1, None, 1, 9, True),
        SettingSpec(
            "maintain_sensitivity",
            HOLDING_MAINTAIN_SENSITIVITY,
            1,
            9,
            1,
            None,
            1,
            9,
            True,
        ),
        SettingSpec(
            "entry_indent",
            HOLDING_ENTRY_INDENT,
            0.0,
            1000 * DISTANCE_SCALE,
            DISTANCE_SCALE,
            "m",
            0,
            1000,
            False,
        ),
        SettingSpec("unit_id", HOLDING_UNIT_ID, 1, 247, 1, None, 1, 247, True),
        SettingSpec("baudrate", HOLDING_BAUDRATE, 1200, 57600, 1, "baud", 1200, 57600, True),
        SettingSpec("parity", HOLDING_PARITY, 0, 2, 1, None, 0, 2, True),
        SettingSpec("active_report", HOLDING_ACTIVE_REPORT, 1, 2, 1, None, 1, 2, True),
        SettingSpec(
            "light_threshold",
            HOLDING_LIGHT_THRESHOLD,
            0.0,
            4200 * TENTHS_SCALE,
            TENTHS_SCALE,
            "lx",
            0,
            4200,
            False,
        ),
        SettingSpec("report_interval", HOLDING_REPORT_INTERVAL, 1, 36000, 1, "s", 1, 36000, True),
    )
}


def _validate(name: str) -> WriteValidator:
    """Build the validator the field carries, so no write path skips it."""
    spec = _SPECS[name]

    def check(value: Any) -> float | int:
        return spec.coerce(value)

    return check


class Settings(Component):
    """The sensor's parameters: read from the holding registers, written on request.

    Every parameter the vendor register map describes is writable; ``0x000D`` is
    not, because its meaning is unknown. Writing goes through
    :meth:`async_write`, which confirms the value by reading it back.
    """

    detection_distance = gauge(
        HOLDING_DETECTION_DISTANCE,
        DISTANCE_SCALE,
        signed=False,
        unit="m",
        writable=_validate("detection_distance"),
    )
    """Furthest distance the sensor reports a target at."""

    shielding_distance = gauge(
        HOLDING_SHIELDING_DISTANCE,
        DISTANCE_SCALE,
        signed=False,
        unit="m",
        writable=_validate("shielding_distance"),
    )
    """Nearest distance the sensor ignores, used to cut off reflections at the edge."""

    entry_delay = gauge(
        HOLDING_ENTRY_DELAY,
        HUNDREDTHS_SCALE,
        signed=False,
        unit="s",
        writable=_validate("entry_delay"),
    )
    """Time a target must be present before the sensor reports it."""

    departure_delay = integer(
        HOLDING_DEPARTURE_DELAY, signed=False, unit="s", writable=_validate("departure_delay")
    )
    """Time without a target before the sensor reports the room as empty."""

    trigger_sensitivity = integer(
        HOLDING_TRIGGER_SENSITIVITY,
        signed=False,
        writable=_validate("trigger_sensitivity"),
    )
    """Sensitivity for the first trigger, 1 to 9."""

    maintain_sensitivity = integer(
        HOLDING_MAINTAIN_SENSITIVITY,
        signed=False,
        writable=_validate("maintain_sensitivity"),
    )
    """Sensitivity that keeps the target detected, 1 to 9."""

    entry_indent = gauge(
        HOLDING_ENTRY_INDENT,
        DISTANCE_SCALE,
        signed=False,
        unit="m",
        writable=_validate("entry_indent"),
    )
    """How far inside the detection distance the first trigger happens."""

    unit_id = integer(HOLDING_UNIT_ID, signed=False, writable=_validate("unit_id"))
    """Address of the sensor on the Modbus bus, 1 to 247."""

    baudrate = integer(HOLDING_BAUDRATE, signed=False, unit="baud", writable=_validate("baudrate"))
    """Bus speed the sensor is configured for."""

    parity = integer(HOLDING_PARITY, signed=False, writable=_validate("parity"))
    """Parity setting: 0 none, 1 odd, 2 even."""

    active_report = integer(
        HOLDING_ACTIVE_REPORT, signed=False, writable=_validate("active_report")
    )
    """Active reporting flag: 1 on, 2 off."""

    light_threshold = gauge(
        HOLDING_LIGHT_THRESHOLD,
        TENTHS_SCALE,
        signed=False,
        unit="lx",
        writable=_validate("light_threshold"),
    )
    """Illuminance threshold for the sensor's own light-gated output; 0 disables it."""

    report_interval = integer(
        HOLDING_REPORT_INTERVAL, signed=False, unit="s", writable=_validate("report_interval")
    )
    """Interval of the sensor's active reporting."""

    def writable_fields(self) -> tuple[SettingSpec, ...]:
        """Every parameter this sensor can be written, in register order."""
        return tuple(_SPECS.values())

    async def async_write(self, name: str, value: Any) -> None:
        """Write one parameter and confirm it by reading the block back.

        The value must be expressed in the same units the reading uses: 30 for
        ``departure_delay``, 6.0 for ``detection_distance``. Nothing is sent
        before the value is known to be within the measured range.

        The sensor reports a new value with a delay of up to half a second, so
        the confirmation read is repeated until the value appears or a second has
        passed.

        Raises ``ValueError`` for a value out of range or of the wrong type,
        ``AttributeError`` for an unknown or read-only parameter, and
        ``WriteVerificationError`` when the device stores something else. Errors
        of the exchange come from ``modbus-connection`` unchanged.

        What this call deliberately does not do: it does not check the device's
        health first, and it does not reconnect when ``unit_id``, ``baudrate`` or
        ``parity`` change — those take effect at once on the device, so the
        caller has to move the link with them. It also does not care that
        ``active_report`` makes the device talk on its own.
        """
        spec = _SPECS.get(name)
        if spec is None:
            raise AttributeError(f"{name!r} is not a writable setting")
        expected = spec.coerce(value)
        await self.write(name, expected)

        deadline = time.monotonic() + CONFIRM_DEADLINE
        while True:
            await self.async_update()
            stored = getattr(self, name)
            if spec.matches(expected, stored):
                return
            if time.monotonic() >= deadline:
                raise WriteVerificationError(name, expected, stored)
            await asyncio.sleep(CONFIRM_PAUSE)
