"""Decoding of the sensor's measurement registers."""

from __future__ import annotations

import pytest
from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit

from mtdx62_modbus_library import DeviceStatus, Mtdx62Device


async def test_reads_all_measurements(mock_modbus_unit: MockModbusUnit) -> None:
    """One read yields presence, illuminance, distance, health and both versions."""
    mock_modbus_unit.input[0] = [1, 1506, 250, 1, 0x0001, 0x0203, 0x0000, 0x0102]

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.presence is True
    assert device.readings.illuminance == 150.6
    assert device.readings.distance == 2.5
    assert device.readings.status_code == 1
    assert device.readings.status is DeviceStatus.OK
    assert device.readings.app_version == "1.2.3"
    assert device.readings.radar_version == "0.1.2"


async def test_values_are_none_before_the_first_read(mock_modbus_unit: MockModbusUnit) -> None:
    """Nothing is invented before the device has answered once."""
    device = Mtdx62Device(mock_modbus_unit)

    assert device.readings.presence is None
    assert device.readings.illuminance is None
    assert device.readings.distance is None
    assert device.readings.status_code is None
    assert device.readings.status is None
    assert device.readings.app_version is None
    assert device.readings.radar_version is None


async def test_zero_distance_is_a_value(mock_modbus_unit: MockModbusUnit) -> None:
    """No target in range is 0 metres, not a missing reading."""
    mock_modbus_unit.input[2] = 0

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.distance == 0.0


async def test_fractional_distance(mock_modbus_unit: MockModbusUnit) -> None:
    """Distance keeps its centimetre resolution."""
    mock_modbus_unit.input[2] = 1234

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.distance == 12.34


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        pytest.param(0, DeviceStatus.SELF_CHECK_IN_PROGRESS, id="self-check"),
        pytest.param(1, DeviceStatus.OK, id="ok"),
        pytest.param(2, DeviceStatus.SELF_TEST_FAILED, id="self-test-failed"),
        pytest.param(3, DeviceStatus.OTHER_FAULT, id="other"),
        pytest.param(4, DeviceStatus.RADAR_FAULT, id="radar"),
        pytest.param(5, DeviceStatus.RS485_FAULT, id="rs485"),
        pytest.param(6, DeviceStatus.RADAR_AND_RS485_FAULT, id="both"),
    ],
)
async def test_known_status_codes(
    mock_modbus_unit: MockModbusUnit, code: int, expected: DeviceStatus
) -> None:
    """Every documented health code decodes to its enum member."""
    mock_modbus_unit.input[3] = code

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.status is expected


@pytest.mark.parametrize(
    ("code", "is_fault"),
    [
        pytest.param(0, False, id="self-check"),
        pytest.param(1, False, id="ok"),
        pytest.param(2, True, id="self-test-failed"),
        pytest.param(6, True, id="both"),
    ],
)
async def test_fault_flag(mock_modbus_unit: MockModbusUnit, code: int, is_fault: bool) -> None:
    """A running sensor is not faulty; anything from 2 upwards is."""
    mock_modbus_unit.input[3] = code

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.status is not None
    assert device.readings.status.is_fault is is_fault


async def test_unknown_status_code_is_kept_raw(mock_modbus_unit: MockModbusUnit) -> None:
    """An undocumented code decodes to no enum but is not lost."""
    mock_modbus_unit.input[3] = 9

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.status is None
    assert device.readings.status_code == 9


@pytest.mark.parametrize(
    ("app_raw", "radar_raw", "app", "radar"),
    [
        pytest.param(0x00010203, 0x00000102, "1.2.3", "0.1.2", id="both"),
        pytest.param(0x00000000, 0x00000000, "0.0.0", "0.0.0", id="zeros"),
        pytest.param(0x00FFFFFF, 0x000A0B0C, "255.255.255", "10.11.12", id="high"),
    ],
)
async def test_versions_are_assembled_from_two_registers(
    mock_modbus_unit: MockModbusUnit,
    app_raw: int,
    radar_raw: int,
    app: str,
    radar: str,
) -> None:
    """Versions read as major.minor.patch from the packed register pair."""
    mock_modbus_unit.input[4] = [(app_raw >> 16) & 0xFFFF, app_raw & 0xFFFF]
    mock_modbus_unit.input[6] = [(radar_raw >> 16) & 0xFFFF, radar_raw & 0xFFFF]

    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    assert device.readings.app_version == app
    assert device.readings.radar_version == radar


async def test_measurements_cost_one_block_read(mock_modbus_unit: MockModbusUnit) -> None:
    """Refreshing the measurements issues exactly one request, eight registers wide."""
    device = Mtdx62Device(mock_modbus_unit)
    await device.async_update_readings()

    events = mock_modbus_unit.read_events
    assert len(events) == 1
    assert events[0].address == 0
    assert events[0].count == 8
    assert events[0].register_type == "input"


async def test_timeout_propagates(mock_modbus_unit: MockModbusUnit) -> None:
    """A silent device surfaces the transport's timeout, not a library-specific error."""
    mock_modbus_unit.fail_requests(ModbusTimeoutError())

    device = Mtdx62Device(mock_modbus_unit)

    with pytest.raises(ModbusTimeoutError):
        await device.async_update_readings()


async def test_readings_are_read_only(mock_modbus_unit: MockModbusUnit) -> None:
    """Measurements come from input registers, which take no writes at all."""
    device = Mtdx62Device(mock_modbus_unit)

    assert device.readings.resolved_fields
    for name, resolved in device.readings.resolved_fields.items():
        assert resolved.field.writable is False, f"{name} is writable"
        with pytest.raises(AttributeError):
            await device.readings.write(name, 1)


async def test_every_setting_but_the_unknown_one_is_writable(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """The register map is the contract: described parameters can be written."""
    device = Mtdx62Device(mock_modbus_unit)

    writable = {spec.address for spec in device.settings.writable_fields()}
    for name, resolved in device.settings.resolved_fields.items():
        assert bool(resolved.field.writable) is (resolved.address in writable), name
