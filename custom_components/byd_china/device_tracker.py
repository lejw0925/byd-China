"""Device Tracker for BYD Vehicle (GCJ-02 → WGS-84 conversion)."""

from __future__ import annotations

import math

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .pybyd_china.models.gps import GpsInfo
from .pybyd_china.models.vehicle import Vehicle

from .const import DOMAIN
from .coordinator import BydDataUpdateCoordinator, BydGpsUpdateCoordinator

# ---------------------------------------------------------------------------
# GCJ-02 to WGS-84 conversion
# ---------------------------------------------------------------------------

PI = math.pi
A = 6378245.0
EE = 0.00669342162296594323


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * (abs(x) ** 0.5)
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * (abs(x) ** 0.5)
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x * PI / 30.0)) * 2.0 / 3.0
    return ret


def _is_out_of_china(lat: float, lon: float) -> bool:
    if lon < 72.004 or lon > 137.8347:
        return True
    if lat < 0.8293 or lat > 55.8271:
        return True
    return False


def gcj02_to_wgs84(gcj_lat: float, gcj_lon: float) -> tuple[float, float]:
    if _is_out_of_china(gcj_lat, gcj_lon):
        return gcj_lat, gcj_lon

    d_lat = _transform_lat(gcj_lon - 105.0, gcj_lat - 35.0)
    d_lon = _transform_lon(gcj_lon - 105.0, gcj_lat - 35.0)

    rad_lat = gcj_lat / 180.0 * PI
    magic = math.sin(rad_lat)
    magic = 1 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((A * (1 - EE)) / (magic * sqrt_magic) * PI)
    d_lon = (d_lon * 180.0) / (A / sqrt_magic * math.cos(rad_lat) * PI)

    wgs_lat = gcj_lat - d_lat
    wgs_lon = gcj_lon - d_lon
    return wgs_lat, wgs_lon


# ---------------------------------------------------------------------------
# Device Tracker entity
# ---------------------------------------------------------------------------


class BydDeviceTracker(CoordinatorEntity, TrackerEntity):
    """BYD Vehicle Device Tracker with GCJ-02 → WGS-84 conversion."""

    _attr_icon = "mdi:car"
    _attr_name = "位置"

    def __init__(
        self,
        coordinator: BydGpsUpdateCoordinator,
        vin: str,
        vehicle: Vehicle,
    ) -> None:
        super().__init__(coordinator)
        self._vin = vin
        self._vehicle = vehicle
        self._attr_unique_id = f"{vin}_dt_location"

    def _get_gps_info(self) -> GpsInfo | None:
        data = self.coordinator.data
        if data is None:
            return None
        if hasattr(data, "latitude") and hasattr(data, "longitude"):
            return data
        return None

    @property
    def latitude(self) -> float | None:
        gps = self._get_gps_info()
        if gps is None or gps.latitude is None or gps.longitude is None:
            return None
        wgs_lat, _ = gcj02_to_wgs84(gps.latitude, gps.longitude)
        return wgs_lat

    @property
    def longitude(self) -> float | None:
        gps = self._get_gps_info()
        if gps is None or gps.latitude is None or gps.longitude is None:
            return None
        _, wgs_lon = gcj02_to_wgs84(gps.latitude, gps.longitude)
        return wgs_lon

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        gps = self._get_gps_info()
        return gps is not None and getattr(gps, "latitude", None) is not None and getattr(gps, "longitude", None) is not None


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BYD device trackers from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators: dict[str, BydDataUpdateCoordinator] = data["coordinators"]
    gps_coordinators: dict[str, BydGpsUpdateCoordinator] = data.get("gps_coordinators", {})

    entities: list[TrackerEntity] = []
    for vin, coordinator in coordinators.items():
        gps_coordinator = gps_coordinators.get(vin)
        if gps_coordinator is not None:
            entities.append(BydDeviceTracker(gps_coordinator, vin, coordinator.vehicle))

    async_add_entities(entities)
