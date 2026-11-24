# mtdx62

Device library for the **MTD062-MB** (5.8 GHz) and **MTD262-MB** (24 GHz) human presence
sensors, spoken to over Modbus RTU or Modbus TCP.

The library models the sensor's registers as typed Python attributes. It reads the whole
measurement block in one Modbus request and keeps the configuration registers separate, so
polling the sensor does not drag along parameters that rarely change.

Built on [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/): the
caller owns the connection and hands over a `ModbusUnit`. The library never opens a socket or a
serial port and has no dependency on Home Assistant.

## Install

```bash
pip install mtdx62-modbus-library
```

## Use

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from mtdx62_modbus_library import Mtdx62Device


async def main() -> None:
    connection = ModbusConnection(ModbusTcpParams(host="192.168.1.50", port=502))
    try:
        device = Mtdx62Device(connection.for_unit(1))

        await device.async_update_readings()
        print(device.readings.presence, device.readings.illuminance, device.readings.distance)

        await device.async_update_settings()
        print(device.settings.detection_distance, device.settings.departure_delay)
    finally:
        await connection.close()


asyncio.run(main())
```

## What it exposes

| Attribute | Meaning | Unit |
|---|---|---|
| `readings.presence` | a person is detected, including someone sitting still | — |
| `readings.illuminance` | ambient light as the sensor sees it | lx |
| `readings.distance` | distance to the detected target | m, centimetre resolution |
| `readings.status_code` | raw health code | — |
| `readings.status` | health code as `DeviceStatus`, `None` when unknown | — || `readings.app_version` | application firmware version, `1.2.3` | — |
| `readings.radar_version` | radar module firmware version | — |
| `settings.*` | detection range, delays, sensitivities, bus address and speed | see `Settings` |

Every attribute is `None` until the first read of its sub-system.

The library only reads: no field is writable, and the sensor's configuration is not changed by
it. Reading the configuration is a separate call (`async_update_settings()`) precisely so that a
5-second poll costs one request.

## Health codes

`readings.status` is a `DeviceStatus` member. A running sensor reports `OK` (1); code 0 is the
transient self-check at power-up, and code 2 and above mean the sensor is broken. `is_fault`
tells the two groups apart, so consumers do not have to remember the boundary.

| Code | Meaning | `is_fault` |
|---|---|---|
| 0 | self-check in progress | no |
| 1 | running | no |
| 2 | self-test failed | yes |
| 3 | other fault | yes |
| 4 | radar module fault | yes |
| 5 | RS485 fault | yes |
| 6 | radar and RS485 fault | yes |

An undocumented code decodes to `None`, while `status_code` keeps the raw number for diagnostics.

> **0.2.0 is a breaking release**: `OK` and `SELF_TEST_FAILED` swapped values, because 0.1.0 read
> the vendor table one row off.

## Errors

The library raises whatever `modbus-connection` raises: a timeout, a protocol error, or a
refusal of the addressed registers. It does not wrap them, so the caller can tell a dead link
from a slow device.

## Supported firmware

Written against the vendor documentation for firmware **1.6**. The register map is in
`openspec/specs/mtdx62-registers/` once the first change is archived, and the raw facts are in
`references/mtdx62/DEVICE-FACTS.md` in the project workspace.

## Tests

Tests run against the in-memory backend of `modbus-connection`, so they need neither hardware
nor Home Assistant:

```bash
pip install -e ".[test]"
pytest
```

## Author

Sergey Astakhov — [sergeyastakhov@mail.ru](mailto:sergeyastakhov@mail.ru),
[github.com/sergeyastakhov](https://github.com/sergeyastakhov).

Source and issues: <https://github.com/sergeyastakhov/mtdx62-modbus-library>. MIT licensed.
