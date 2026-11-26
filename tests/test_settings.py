"""Reading the sensor's configuration registers."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from mtdx62_modbus_library import Mtdx62Device


async def test_reads_settings(mock_modbus_unit: MockModbusUnit) -> None:
    """Every parameter decodes with its own scale and unit."""
    mock_modbus_unit.holding[0] = [
        600,  # detection distance, 6.00 m
        60,  # shielding distance, 0.60 m
        10,  # entry delay, 0.10 s
        30,  # departure delay, 30 s
        7,  # trigger sensitivity
        7,  # maintain sensitivity
        60,  # entry indent, 0.60 m
        1,  # unit id
        9600,  # baudrate
        1,  # parity: odd
        2,  # active report: off
        100,  # light threshold, 10.0 lx (tenths of a lux)
        600,  # report interval, 600 s
    ]

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_settings()

    assert device.settings.detection_distance == 6.0
    assert device.settings.shielding_distance == 0.6
    assert device.settings.entry_delay == 0.1
    assert device.settings.departure_delay == 30
    assert device.settings.trigger_sensitivity == 7
    assert device.settings.maintain_sensitivity == 7
    assert device.settings.entry_indent == 0.6
    assert device.settings.unit_id == 1
    assert device.settings.baudrate == 9600
    assert device.settings.parity == 1
    assert device.settings.active_report == 2
    assert device.settings.light_threshold == 10.0
    assert device.settings.report_interval == 600


async def test_settings_are_none_before_the_first_read(mock_modbus_unit: MockModbusUnit) -> None:
    """Parameters are not invented before they are read."""
    device = Mtdx62Device(mock_modbus_unit)

    assert device.settings.detection_distance is None
    assert device.settings.baudrate is None


async def test_settings_are_not_read_with_the_measurements(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Polling the measurements leaves the holding registers alone."""
    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert mock_modbus_unit.read_events
    assert all(event.register_type == "input" for event in mock_modbus_unit.read_events)
    assert device.settings.detection_distance is None


async def test_settings_cost_one_block_read(mock_modbus_unit: MockModbusUnit) -> None:
    """The whole parameter block comes back in one request."""
    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_settings()

    events = mock_modbus_unit.read_events
    assert len(events) == 1
    assert events[0].register_type == "holding"
    assert events[0].address == 0
    assert events[0].count == 13
