# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Home Assistant custom integration for BYD (比亚迪) vehicles in China. Cloud-polling integration (`iot_class: cloud_polling`) that pulls telemetry and GPS data from the BYD China API (`dilinksuperappserver-cn.byd.auto`). The `pybyd` library is vendored as `pybyd_china/` inside the component directory.

## Project structure

```
custom_components/byd_china/
├── pybyd_china/          # Vendored pybyd library (was external, now in-tree)
│   ├── client.py         # BydClient — async client for BYD vehicle API
│   ├── config.py         # BydConfig, DeviceProfile
│   ├── session.py        # Session (auth token state)
│   ├── _api/             # Per-endpoint API modules (login, realtime, gps, etc.)
│   ├── _crypto/          # AES, Bangcle, WBSK, signing, hashing
│   ├── models/           # Pydantic models (Vehicle, VehicleRealtimeData, GpsInfo, HvacStatus, etc.)
│   ├── _state_engine.py  # VehicleSnapshot, VehicleStateEngine
│   ├── _capabilities/    # Typed capability namespaces (lock, hvac, seat, etc.)
│   └── data/             # bangcle_tables.bin (crypto table)
├── __init__.py           # async_setup_entry, services, config migration
├── config_flow.py        # Config flow (username/password), reauth, reconfigure
├── coordinator.py        # BydApi (client wrapper), BydDataUpdateCoordinator, BydGpsUpdateCoordinator
├── entity.py             # BydVehicleEntity base mixin with snapshot helpers
├── sensor.py             # ~50 sensors + BydDeviceTracker
├── number.py             # Runtime-configurable poll-interval NumberEntity for telemetry + GPS
├── binary_sensor.py      # Stub — empty async_setup_entry (all moved to text sensors)
├── device_tracker.py     # Stub — empty async_setup_entry (device_tracker is in sensor.py)
├── device_fingerprint.py # Generates realistic Android device profiles (IMEI/MAC) from device_pool.json
├── device_pool.json      # Samsung device pool for fingerprint generation
├── const.py              # Constants, China-only config defaults
├── strings.json          # English display strings for config flow and entities
├── services.yaml         # Service definitions: fetch_realtime, fetch_gps
└── manifest.json         # Integration metadata (version 0.0.2, domain byd_china)
```

## Architecture

**Two-coordinator model per vehicle (VIN)**:
- `BydDataUpdateCoordinator` — polls telemetry via `BydClient.get_vehicle_realtime()` every `CONF_POLL_INTERVAL` seconds (default 300). Data type: `VehicleSnapshot`.
- `BydGpsUpdateCoordinator` — polls GPS via `BydClient.get_gps_info()` every `CONF_GPS_POLL_INTERVAL` seconds (default 300). Data type: `GpsInfo`.

**Data flow**:
1. `async_setup_entry` creates a `BydApi` instance wrapping `BydClient` lifecycle (session caching, debug dumps).
2. Calls `client.get_vehicles()` to discover VINs, creates a coordinator pair per VIN.
3. Runs first refresh on all coordinators, then forwards platform setup to `sensor`, `binary_sensor`, `device_tracker`, `number`.
4. Sensors read from coordinator data via `BydVehicleEntity` helpers (`_get_realtime()`, `_get_gps()`, `_snapshot()`).

**China mode**: `BydConfig.is_china_region` auto-detects from `base_url` (`cn.byd.auto`) and routes to CN endpoints (WBSK crypto, `/app/auth/login`, CN-specific API paths).

## Key behaviors

- **Device fingerprinting**: On first setup, `device_fingerprint.py` generates a random Samsung Android device profile (IMEI with valid Luhn check digit, locally-administered MAC). Stored in config entry data as `CONF_DEVICE_PROFILE` and passed into `BydConfig.device`.
- **GCJ-02 → WGS-84**: GPS coordinates from the CN API use GCJ-02 (Mars coordinates). `sensor.py` converts them to WGS-84 in `BydDeviceTracker` for correct map display. Raw GCJ-02 values are also exposed as sensor entities.
- **Services**: Two services (`byd_china.fetch_realtime`, `byd_china.fetch_gps`) accept `device_id` and force-refresh the matching coordinator.
- **Config migration**: `async_migrate_entry` handles migrations up to version 4, normalizing config data to China defaults.

## Vendored pybyd_china

All internal imports use relative paths (`from .models._base import ...`). The vendored copy was adapted from `pyBYD`:
- `importlib.resources.files("pybyd")` → `Path(__file__).parent / "data" / ...` for data file loading
- `version("pybyd")` in `__init__.py` falls back to `"0+local"` since the package is vendored
- `wbsk_tables.json` is expected at `pybyd_china/data/wbsk_tables.json` (may need to be provided separately)

## Development

This is a Home Assistant custom component. To test:
1. Symlink or copy `custom_components/byd_china/` into a Home Assistant instance's `custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via UI (Settings → Devices & Services → Add Integration → BYD China).
4. Check logs with `logger.set_level` for `custom_components.byd_china` to DEBUG.

No build step, linter, or test suite exists in this repository.
