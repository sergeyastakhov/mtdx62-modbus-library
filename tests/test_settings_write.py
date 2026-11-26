"""Writing the sensor's parameters."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from modbus_connection import IllegalDataValueError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit, WriteEvent

from mtdx62_modbus_library import Mtdx62Device, WriteVerificationError

DEFAULTS = [
    600,  # 0x0000 detection distance, 6.00 m
    60,  # 0x0001 shielding distance, 0.60 m
    10,  # 0x0002 entry delay, 0.10 s
    30,  # 0x0003 departure delay, 30 s
    7,  # 0x0004 trigger sensitivity
    7,  # 0x0005 maintain sensitivity
    60,  # 0x0006 entry indent, 0.60 m
    1,  # 0x0007 unit id
    9600,  # 0x0008 baudrate
    0,  # 0x0009 parity: none
    2,  # 0x000A active report: off
    0,  # 0x000B light threshold: off
    600,  # 0x000C report interval, 600 s
]


@pytest.fixture
def unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A sensor at its factory settings."""
    for address, value in enumerate(DEFAULTS):
        mock_modbus_unit.holding[address] = value
    return mock_modbus_unit


@pytest.fixture
def device(unit: MockModbusUnit) -> Mtdx62Device:
    """The device object on that unit."""
    return Mtdx62Device(unit)


def writes(unit: MockModbusUnit) -> list[WriteEvent]:
    """Every write the library sent."""
    seen: list[WriteEvent] = []
    unit.on_write(seen.append)
    return seen


def test_writable_fields_are_in_register_order(device: Mtdx62Device) -> None:
    """Every described parameter is listed once, from the first address on."""
    specs = device.settings.writable_fields()

    assert [spec.address for spec in specs] == list(range(13))
    assert [spec.name for spec in specs] == [
        "detection_distance",
        "shielding_distance",
        "entry_delay",
        "departure_delay",
        "trigger_sensitivity",
        "maintain_sensitivity",
        "entry_indent",
        "unit_id",
        "baudrate",
        "parity",
        "active_report",
        "light_threshold",
        "report_interval",
    ]


def test_a_spec_carries_limits_and_units(device: Mtdx62Device) -> None:
    """A caller builds entities from these numbers, not from the register map."""
    spec = device.settings.writable_fields()[0]

    assert (spec.minimum, spec.maximum, spec.step, spec.unit) == (0.6, 10.0, 0.01, "m")
    assert (spec.raw_minimum, spec.raw_maximum) == (60, 1000)


def test_a_spec_cannot_be_edited(device: Mtdx62Device) -> None:
    """The list is a contract, not a scratch pad."""
    spec = device.settings.writable_fields()[0]

    with pytest.raises(FrozenInstanceError):
        spec.minimum = 1.0  # type: ignore[misc]


def test_the_unknown_register_is_not_writable(device: Mtdx62Device) -> None:
    """Nothing writes to 0x000D while its meaning is unknown."""
    addresses = {spec.address for spec in device.settings.writable_fields()}

    assert 0x0D not in addresses


async def test_a_value_out_of_range_never_reaches_the_bus(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """The check runs before the first byte, so the device sees nothing."""
    seen = writes(unit)

    with pytest.raises(ValueError, match="between 5 and 1500"):
        await device.settings.async_write("departure_delay", 2)

    assert seen == []
    assert unit.read_events == []
    assert unit.holding[3] == 30


@pytest.mark.parametrize("value", ["шесть", None, [30], True])
async def test_a_value_of_the_wrong_kind_is_refused(
    device: Mtdx62Device, unit: MockModbusUnit, value: object
) -> None:
    """A string, a list or a bool is not a number for this register."""
    seen = writes(unit)

    with pytest.raises(ValueError):
        await device.settings.async_write("detection_distance", value)

    assert seen == []
    assert unit.read_events == []


async def test_an_infinite_value_is_refused(device: Mtdx62Device, unit: MockModbusUnit) -> None:
    """Infinity has no register encoding, so it never leaves the library."""
    seen = writes(unit)

    with pytest.raises(ValueError, match="finite"):
        await device.settings.async_write("detection_distance", float("inf"))

    assert seen == []


def test_a_field_without_a_reading_never_matches(device: Mtdx62Device) -> None:
    """Before any read there is no stored value to compare with."""
    spec = device.settings.writable_fields()[3]

    assert spec.matches(40, None) is False


async def test_an_unknown_name_is_an_attribute_error(device: Mtdx62Device) -> None:
    """Asking to write something that does not exist is a programmer's mistake."""
    with pytest.raises(AttributeError, match="not a writable setting"):
        await device.settings.async_write("mac", 1)


async def test_the_low_level_write_cannot_bypass_the_check(device: Mtdx62Device) -> None:
    """The field carries the validator, so the raw component path is covered too."""
    with pytest.raises(ValueError):
        await device.settings.write("departure_delay", 2)


async def test_a_written_value_is_confirmed_by_reading(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """The register holds the value and the cache shows it without a poll."""
    await device.settings.async_write("departure_delay", 40)

    assert unit.holding[3] == 40
    assert device.settings.departure_delay == 40


async def test_a_scaled_value_round_trips(device: Mtdx62Device, unit: MockModbusUnit) -> None:
    """Six metres and ten centimetres survive the trip through the scale."""
    await device.settings.async_write("detection_distance", 6.1)

    assert unit.holding[0] == 610
    assert device.settings.detection_distance == 6.1


async def test_a_value_the_device_clamped_is_reported(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """Accepted frame is not the same as stored value."""
    unit.on_write(lambda event: unit.holding.__setitem__(event.address, 7))

    with pytest.raises(WriteVerificationError) as caught:
        await device.settings.async_write("trigger_sensitivity", 9)

    assert caught.value.requested == 9
    assert caught.value.stored == 7
    assert caught.value.field == "trigger_sensitivity"


async def test_the_cache_comes_from_one_read(device: Mtdx62Device, unit: MockModbusUnit) -> None:
    """Every field reflects the same reading, not a mix of old and new."""
    unit.holding[1] = 80
    unit.holding[4] = 4

    await device.settings.async_write("departure_delay", 45)

    assert device.settings.shielding_distance == 0.8
    assert device.settings.trigger_sensitivity == 4
    assert device.settings.departure_delay == 45


async def test_the_state_register_is_not_read(device: Mtdx62Device, unit: MockModbusUnit) -> None:
    """One write and one block read: the library does not police the device."""
    unit.input[3] = 2

    await device.settings.async_write("departure_delay", 40)

    assert [(event.register_type, event.address) for event in unit.read_events] == [("holding", 0)]


async def test_a_rejected_write_keeps_the_old_cache(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """The device refused the frame, so nothing is known about the register."""
    await device.settings.async_update()
    unit.fail_write(3, IllegalDataValueError("no such value"))

    with pytest.raises(IllegalDataValueError):
        await device.settings.async_write("departure_delay", 40)

    assert device.settings.departure_delay == 30


async def test_a_silent_device_raises_the_transport_error(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """A timeout stays a timeout and does not become a verification failure."""
    unit.fail_write(3, ModbusTimeoutError("no answer"))

    with pytest.raises(ModbusTimeoutError):
        await device.settings.async_write("departure_delay", 40)


async def test_the_bus_address_can_be_written_without_touching_the_unit(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """The register changes; the link the caller owns does not."""
    await device.settings.async_write("unit_id", 5)

    assert unit.holding[7] == 5
    assert device.settings.unit_id == 5


async def test_the_baud_rate_can_be_written_without_touching_the_unit(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """Configured speed is data; the live connection is the caller's business."""
    await device.settings.async_write("baudrate", 19200)

    assert unit.holding[8] == 19200
    assert device.settings.baudrate == 19200


async def test_the_parity_must_be_one_of_the_three_codes(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """Three is not a parity code."""
    seen = writes(unit)

    with pytest.raises(ValueError):
        await device.settings.async_write("parity", 3)

    assert seen == []


async def test_active_reporting_can_be_switched_on(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """A caller that wants push mode can have it; the library does not police it."""
    await device.settings.async_write("active_report", 1)

    assert unit.holding[10] == 1


async def test_the_light_threshold_round_trips(device: Mtdx62Device, unit: MockModbusUnit) -> None:
    """Ten lux go in as thousandths, as the register map says."""
    await device.settings.async_write("light_threshold", 10.0)

    assert unit.holding[11] == 100
    assert device.settings.light_threshold == 10.0


async def test_the_light_threshold_can_be_switched_off(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """Zero disables the sensor's own light gate."""
    await device.settings.async_write("light_threshold", 0)

    assert unit.holding[11] == 0


async def test_a_mismatch_does_not_try_the_neighbour(
    device: Mtdx62Device, unit: MockModbusUnit
) -> None:
    """No guessing: the neighbouring register is never written as a fallback."""
    unit.on_write(lambda event: unit.holding.__setitem__(event.address, 500))
    before = unit.holding[12]

    with pytest.raises(WriteVerificationError):
        await device.settings.async_write("light_threshold", 10.0)

    assert unit.holding[12] == before
