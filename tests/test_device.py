"""The device object: sub-systems, raw dump and independence from Home Assistant."""

from __future__ import annotations

import subprocess
import sys

from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from mtdx62_modbus_library import ALL, READINGS, Mtdx62Device, Settings


def test_device_exposes_both_subsystems(mock_modbus_unit: MockModbusUnit) -> None:
    """Measurements and parameters are reachable without touching the bus."""
    device = Mtdx62Device(mock_modbus_unit)

    assert isinstance(device.settings, Settings)
    assert READINGS == ("readings",)
    assert ALL == ("readings", "settings")


async def test_raw_dump_keeps_addresses(mock_modbus_unit: MockModbusUnit) -> None:
    """The raw dump reports register space and address, so a reading can be replayed."""
    mock_modbus_unit.input[0] = [1, 42, 250, 0, 0x0001, 0x0203, 0x0000, 0x0102]
    mock_modbus_unit.holding[0] = [600]

    device = Mtdx62Device(mock_modbus_unit)
    raw = await device.async_read_raw()

    assert raw["input"][0] == 1
    assert raw["input"][2] == 250
    assert raw["holding"][0] == 600


async def test_raw_dump_can_be_replayed(mock_modbus_unit: MockModbusUnit) -> None:
    """A dump taken from one device decodes the same way in a fresh mock."""
    mock_modbus_unit.input[0] = [1, 42, 250, 0, 0x0001, 0x0203, 0x0000, 0x0102]
    device = Mtdx62Device(mock_modbus_unit)
    dump = await device.async_read_raw(READINGS)

    replay_unit = MockModbusConnection().for_unit(1)
    replay_unit.load_raw(dump)
    replay = Mtdx62Device(replay_unit)
    await replay.async_update_readings()

    assert replay.readings.presence is True
    assert replay.readings.illuminance == 42
    assert replay.readings.distance == 2.5


def test_import_does_not_pull_home_assistant() -> None:
    """The library stays usable without Home Assistant installed."""
    code = "import mtdx62_modbus_library, sys; print('homeassistant' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "False"
