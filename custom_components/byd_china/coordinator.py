"""Data coordinators for BYD China."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .pybyd_china.client import BydClient
from .pybyd_china.config import BydConfig, DeviceProfile
from .pybyd_china.exceptions import (
    BydApiError,
    BydAuthenticationError,
    BydTransportError,
)
from .pybyd_china.models.gps import GpsInfo
from .pybyd_china.models.hvac import HvacStatus
from .pybyd_china.models.realtime import VehicleRealtimeData
from .pybyd_china.models.vehicle import Vehicle
from .pybyd_china._state_engine import VehicleSnapshot

from .const import (
    CONF_BASE_URL,
    CONF_COUNTRY_CODE,
    CONF_DEBUG_DUMPS,
    CONF_DEVICE_PROFILE,
    CONF_LANGUAGE,
    CONF_TARGET_BRAND,
    DEFAULT_DEBUG_DUMPS,
    DEFAULT_LANGUAGE,
    DEFAULT_TARGET_BRAND,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_HA_EVENT_COMMAND_LIFECYCLE: str = f"{DOMAIN}_command_lifecycle"

_AUTH_ERRORS = (BydAuthenticationError,)
_RECOVERABLE_ERRORS = (BydApiError, BydTransportError)
# API error codes indicating the account is not the vehicle owner
# (authorized/shared accounts cannot access realtime/GPS via HTTP)
_NON_OWNER_CODES = frozenset({"240", "216"})


def get_vehicle_display(vehicle: Vehicle) -> str:
    """Return a human-readable display name for a vehicle."""
    if vehicle.auto_plate:
        return vehicle.auto_plate
    if vehicle.auto_alias:
        return vehicle.auto_alias
    if vehicle.model_name:
        return vehicle.model_name
    return vehicle.vin[-6:] if vehicle.vin else "BYD"


class BydApi:
    """Thin wrapper around the pybyd client.

    Manages client lifecycle, exception translation, and debug dump writing.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, session: Any) -> None:
        self._hass = hass
        self._entry = entry
        self._http_session = session
        time_zone = hass.config.time_zone or "UTC"
        device_data = entry.data.get(CONF_DEVICE_PROFILE, {})
        device = DeviceProfile(**device_data) if device_data else DeviceProfile()
        self._config = BydConfig(
            username=entry.data["username"],
            password=entry.data["password"],
            base_url=entry.data[CONF_BASE_URL],
            country_code=entry.data.get(CONF_COUNTRY_CODE, "CN"),
            language=entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            time_zone=time_zone,
            control_pin=None,
            target_brand=entry.data.get(CONF_TARGET_BRAND, DEFAULT_TARGET_BRAND),
            device=device,
        )
        self._client: BydClient | None = None
        self._debug_dumps_enabled = entry.options.get(
            CONF_DEBUG_DUMPS,
            DEFAULT_DEBUG_DUMPS,
        )
        self._debug_dump_dir = Path(hass.config.path(".storage/byd_vehicle_debug"))
        _LOGGER.debug(
            "BYD API initialized: entry_id=%s, base_url=%s, target_brand=%s",
            entry.entry_id,
            entry.data[CONF_BASE_URL],
            self._config.target_brand,
        )

    # ------------------------------------------------------------------
    # Debug dumps
    # ------------------------------------------------------------------

    def _write_debug_dump(self, category: str, payload: dict[str, Any]) -> None:
        if not self._debug_dumps_enabled:
            return
        try:
            self._debug_dump_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S%fZ")
            file_path = self._debug_dump_dir / f"{timestamp}_{category}.json"
            file_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to write BYD debug dump.", exc_info=True)

    async def _async_write_debug_dump(
        self,
        category: str,
        payload: dict[str, Any],
    ) -> None:
        await self._hass.async_add_executor_job(
            self._write_debug_dump, category, payload
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def config(self) -> BydConfig:
        return self._config

    @property
    def debug_dumps_enabled(self) -> bool:
        return self._debug_dumps_enabled

    async def async_write_debug_dump(
        self, category: str, payload: dict[str, Any]
    ) -> None:
        await self._async_write_debug_dump(category, payload)

    async def async_shutdown(self) -> None:
        await self._invalidate_client()

    async def _ensure_client(self) -> BydClient:
        if self._client is None:
            _LOGGER.debug(
                "Creating new pybyd client: entry_id=%s",
                self._entry.entry_id,
            )
            self._client = BydClient(
                self._config,
                session=self._http_session,
            )
            await self._client.async_start()
            await self._client.login()
        return self._client

    async def _invalidate_client(self) -> None:
        if self._client is not None:
            _LOGGER.debug(
                "Invalidating pybyd client: entry_id=%s",
                self._entry.entry_id,
            )
            try:
                await self._client.async_close()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Error closing pybyd client", exc_info=True)
            self._client = None

    async def async_call(
        self,
        handler: Any,
        *,
        vin: str | None = None,
        command: str | None = None,
    ) -> Any:
        """Execute a pybyd call with error translation."""
        call_started = perf_counter()
        _LOGGER.debug(
            "BYD API call started: entry_id=%s, vin=%s, command=%s",
            self._entry.entry_id,
            vin[-6:] if vin else "-",
            command or "-",
        )
        try:
            client = await self._ensure_client()
            result = await handler(client)
            _LOGGER.debug(
                "BYD API call succeeded: entry_id=%s, vin=%s, "
                "command=%s, duration_ms=%.1f",
                self._entry.entry_id,
                vin[-6:] if vin else "-",
                command or "-",
                (perf_counter() - call_started) * 1000,
            )
            return result
        except BydAuthenticationError as exc:
            await self._invalidate_client()
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except BydTransportError as exc:
            await self._invalidate_client()
            raise UpdateFailed(str(exc)) from exc
        except BydApiError as exc:
            raise UpdateFailed(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug(
                "BYD API call failed: entry_id=%s, vin=%s, command=%s, "
                "duration_ms=%.1f, error=%s",
                self._entry.entry_id,
                vin[-6:] if vin else "-",
                command or "-",
                (perf_counter() - call_started) * 1000,
                type(exc).__name__,
            )
            raise


class BydDataUpdateCoordinator(DataUpdateCoordinator[VehicleSnapshot | None]):
    """Coordinator for telemetry updates for a single VIN."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: BydApi,
        vin: str,
        vehicle_info: dict[str, Any],
        poll_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_telemetry_{vin[-6:]}",
            update_interval=timedelta(seconds=poll_interval),
        )
        self._api = api
        self._vin = vin
        self._vehicle_info = vehicle_info
        self._fixed_interval = timedelta(seconds=poll_interval)
        self._polling_enabled = True
        self._force_next_refresh = False

        self._vehicle = Vehicle.model_validate(vehicle_info) if vehicle_info else Vehicle(vin=vin)

        # BydCar is not used in China mode (no state engine / MQTT push),
        # but entity files reference coordinator.car. Provide a stub.
        self._car: Any = None

    @property
    def vehicle(self) -> Vehicle:
        """Return the Vehicle model for entity compatibility."""
        return self._vehicle

    @property
    def car(self) -> Any:
        """Return the BydCar aggregate (stub in China mode).

        In the overseas integration, BydCar provides typed capability
        namespaces (lock, hvac, seat, etc.) backed by the state engine.
        In China mode we use BydClient.remote_control() directly, so
        this returns None. Entity files that call car.lock.lock() etc.
        are adapted to use coordinator.api instead.
        """
        return self._car

    def capability_available(self, key: str) -> bool:
        """Check if a capability is available.

        For location/GPS, always return True.
        For control commands, always return False (control removed).
        """
        if key in ("location", "gps"):
            return True
        return False

    @property
    def vehicle_info(self) -> dict[str, Any]:
        return self._vehicle_info

    @property
    def vin(self) -> str:
        return self._vin

    async def _async_update_data(self) -> VehicleSnapshot | None:
        """Fetch realtime telemetry data and build a VehicleSnapshot."""
        _LOGGER.debug("Telemetry refresh started: vin=%s", self._vin[-6:])
        force = self._force_next_refresh
        self._force_next_refresh = False

        if not self._polling_enabled and not force:
            return self.data

        try:
            client = await self._api._ensure_client()
            realtime_data = await client.get_vehicle_realtime(self._vin)

            if self._api.debug_dumps_enabled:
                self.hass.async_create_task(
                    self._api.async_write_debug_dump("telemetry", {"vin": self._vin, "realtime": realtime_data.model_dump() if realtime_data else None})
                )

            snapshot = VehicleSnapshot(
                vehicle=self._vehicle,
                realtime=realtime_data,
                hvac=getattr(realtime_data, "hvac", None) if realtime_data else None,
            )

            _LOGGER.debug("Telemetry refresh succeeded: vin=%s", self._vin[-6:])
            return snapshot
        except BydApiError as exc:
            if getattr(exc, "code", "") in _NON_OWNER_CODES:
                _LOGGER.debug("Telemetry not available for authorized account: %s", exc)
                return self.data
            raise UpdateFailed(str(exc)) from exc
        except _AUTH_ERRORS:
            raise
        except _RECOVERABLE_ERRORS as exc:
            raise UpdateFailed(str(exc)) from exc

    # Polling control
    @property
    def polling_enabled(self) -> bool:
        return self._polling_enabled

    @property
    def poll_interval_seconds(self) -> int:
        return int(self._fixed_interval.total_seconds())

    def set_poll_interval(self, seconds: int) -> None:
        self._fixed_interval = timedelta(seconds=seconds)
        if self._polling_enabled:
            self.update_interval = self._fixed_interval
        self.async_update_listeners()

    def set_polling_enabled(self, enabled: bool) -> bool:
        was_enabled = self._polling_enabled
        self._polling_enabled = bool(enabled)
        self.update_interval = self._fixed_interval if self._polling_enabled else None
        return not was_enabled and self._polling_enabled

    async def async_set_polling_enabled(self, enabled: bool) -> None:
        if self.set_polling_enabled(enabled):
            await self.async_request_refresh()

    async def async_force_refresh(self) -> None:
        self._force_next_refresh = True
        await self.async_request_refresh()


class BydGpsUpdateCoordinator(DataUpdateCoordinator[GpsInfo | None]):
    """Coordinator for GPS updates for a single VIN (CN single-request)."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: BydApi,
        vin: str,
        poll_interval: int,
        vehicle_info: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_gps_{vin[-6:]}",
            update_interval=timedelta(seconds=poll_interval),
        )
        self._api = api
        self._vin = vin
        self._vehicle_info = vehicle_info or {}
        self._fixed_interval = timedelta(seconds=poll_interval)
        self._polling_enabled = True
        self._force_next_refresh = False

    @property
    def polling_enabled(self) -> bool:
        return self._polling_enabled

    @property
    def poll_interval_seconds(self) -> int:
        return int(self._fixed_interval.total_seconds())

    def set_poll_interval(self, seconds: int) -> None:
        self._fixed_interval = timedelta(seconds=seconds)
        if self._polling_enabled:
            self.update_interval = self._fixed_interval
        self.async_update_listeners()

    def set_polling_enabled(self, enabled: bool) -> bool:
        was_enabled = self._polling_enabled
        self._polling_enabled = bool(enabled)
        self.update_interval = self._fixed_interval if self._polling_enabled else None
        return not was_enabled and self._polling_enabled

    async def async_set_polling_enabled(self, enabled: bool) -> None:
        if self.set_polling_enabled(enabled):
            await self.async_request_refresh()

    async def async_force_refresh(self) -> None:
        self._force_next_refresh = True
        await self.async_request_refresh()

    async def _async_update_data(self) -> GpsInfo | None:
        """Fetch GPS data (CN single-request endpoint)."""
        _LOGGER.debug("GPS refresh started: vin=%s", self._vin[-6:])
        force = self._force_next_refresh
        self._force_next_refresh = False

        if not self._polling_enabled and not force:
            _LOGGER.debug("GPS refresh skipped (polling disabled): vin=%s", self._vin[-6:])
            return self.data

        try:
            client = await self._api._ensure_client()
            gps = await client.get_gps_info(self._vin)

            if self._api.debug_dumps_enabled:
                self.hass.async_create_task(
                    self._api.async_write_debug_dump("gps", {"vin": self._vin, "gps": gps.model_dump() if gps else None})
                )

            if gps is not None:
                _LOGGER.debug(
                    "GPS refresh succeeded: vin=%s lat=%s lon=%s",
                    self._vin[-6:], gps.latitude, gps.longitude,
                )
            else:
                _LOGGER.warning("GPS refresh returned None: vin=%s", self._vin[-6:])
            return gps
        except BydApiError as exc:
            if getattr(exc, "code", "") in _NON_OWNER_CODES:
                _LOGGER.debug("GPS not available for authorized account: %s", exc)
                return self.data
            _LOGGER.warning("GPS fetch error: vin=%s code=%s msg=%s", self._vin[-6:], getattr(exc, "code", ""), exc)
            return self.data
        except _AUTH_ERRORS:
            raise
        except _RECOVERABLE_ERRORS as exc:
            _LOGGER.warning("GPS fetch error: vin=%s type=%s msg=%s", self._vin[-6:], type(exc).__name__, exc)
            return self.data
        except Exception:  # noqa: BLE001
            _LOGGER.exception("GPS fetch unexpected error: vin=%s", self._vin[-6:])
            return self.data
