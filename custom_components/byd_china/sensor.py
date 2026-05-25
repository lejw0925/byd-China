"""Sensors for BYD Vehicle."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .pybyd_china.models.gps import GpsInfo
from .pybyd_china.models.vehicle import Vehicle

from .const import DOMAIN
from .coordinator import BydDataUpdateCoordinator, BydGpsUpdateCoordinator, get_vehicle_display
from .entity import BydVehicleEntity

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

FieldValidator = Callable[[Any, Any], Any]


def _normalize_epoch(value: Any) -> datetime | None:
    """Ensure a pre-parsed BydTimestamp is UTC-aware, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return None


@dataclass(frozen=True, kw_only=True)
class BydSensorDescription(SensorEntityDescription):
    """Describe a BYD sensor."""

    source: str = "realtime"
    attr_key: str | None = None
    value_fn: Callable[[Any], Any] | None = None
    validator_fn: FieldValidator | None = None
    use_gps_coordinator: bool = False


# ---------------------------------------------------------------------------
# Value conversion helpers
# ---------------------------------------------------------------------------

_LEADING_NUMBER_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)")


def _status_text(attr: str) -> Callable[[Any], str | None]:
    def _fn(obj: Any) -> str | None:
        val = getattr(obj, attr, None)
        if val is None:
            return None
        raw = getattr(val, "value", val)
        if raw is None:
            return None
        if raw < 0:
            return "不可用"
        if raw == 0:
            return "正常"
        return "异常"
    return _fn


def _door_text(attr: str) -> Callable[[Any], str | None]:
    def _fn(obj: Any) -> str | None:
        val = getattr(obj, attr, None)
        if val is None:
            return None
        raw = getattr(val, "value", val)
        if raw is None or raw < 0:
            return None
        if raw == 1:
            return "打开"
        return "关闭"
    return _fn


def _lock_text(attr: str) -> Callable[[Any], str | None]:
    def _fn(obj: Any) -> str | None:
        val = getattr(obj, attr, None)
        if val is None:
            return None
        raw = getattr(val, "value", val)
        if raw is None or raw < 0:
            return None
        if raw == 2:
            return "已锁定"
        if raw == 1:
            return "已解锁"
        return None
    return _fn


def _window_text(attr: str) -> Callable[[Any], str | None]:
    def _fn(obj: Any) -> str | None:
        val = getattr(obj, attr, None)
        if val is None:
            return None
        raw = getattr(val, "value", val)
        if raw is None:
            return None
        if raw < 0:
            return "未配备"
        if raw == 2:
            return "打开"
        return "关闭"
    return _fn


def _tire_status_text(attr: str) -> Callable[[Any], str | None]:
    def _fn(obj: Any) -> str | None:
        val = getattr(obj, attr, None)
        if val is None:
            return None
        raw = getattr(val, "value", val)
        if raw is None or raw < 0:
            return None
        if raw == 0:
            return "正常"
        return "异常"
    return _fn


def _raw_int(attr: str) -> Callable[[Any], int | None]:
    def _fn(obj: Any) -> int | None:
        val = getattr(obj, attr, None)
        if val is None:
            return None
        return getattr(val, "value", val)
    return _fn


def _parse_numeric_string(attr: str) -> Callable[[Any], float | None]:
    def _convert(obj: Any) -> float | None:
        value = getattr(obj, attr, None)
        if value is None or value == "--":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            if isinstance(value, str):
                match = _LEADING_NUMBER_RE.match(value)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        pass
            return None
    return _convert


# =============================================
# SENSOR DESCRIPTIONS
# =============================================

SENSOR_DESCRIPTIONS: tuple[BydSensorDescription, ...] = (
    # --- 车辆信息 ---
    BydSensorDescription(key="vin", name="VIN", source="realtime", icon="mdi:car"),
    BydSensorDescription(key="c_car_type", name="车型", source="realtime", icon="mdi:car-side"),
    BydSensorDescription(key="auto_plate", name="车牌号", source="realtime", icon="mdi:card-text"),
    BydSensorDescription(key="auto_out_color", name="外观颜色", source="realtime", icon="mdi:palette"),
    BydSensorDescription(key="vehicle_image", name="车辆图片", source="realtime", icon="mdi:image"),
    BydSensorDescription(key="channel", name="品牌", source="realtime", icon="mdi:tag"),
    # --- 系统状态 ---
    BydSensorDescription(key="power_battery", name="动力电池", source="realtime", icon="mdi:battery-outline", value_fn=_status_text("power_battery")),
    BydSensorDescription(key="charging_system", name="充电系统", source="realtime", icon="mdi:ev-station", value_fn=_status_text("charging_system")),
    BydSensorDescription(key="srs", name="安全气囊", source="realtime", icon="mdi:airbag", value_fn=_status_text("srs")),
    BydSensorDescription(key="esp", name="ESP", source="realtime", icon="mdi:car-traction-control", value_fn=_status_text("esp")),
    BydSensorDescription(key="braking_system", name="制动系统", source="realtime", icon="mdi:car-brake-alert", value_fn=_status_text("braking_system")),
    BydSensorDescription(key="abs_warning", name="ABS", source="realtime", icon="mdi:car-brake-abs", value_fn=_status_text("abs_warning")),
    BydSensorDescription(key="steering_system", name="转向系统", source="realtime", icon="mdi:steering", value_fn=_status_text("steering_system")),
    BydSensorDescription(key="power_system", name="动力系统", source="realtime", icon="mdi:flash", value_fn=_status_text("power_system")),
    BydSensorDescription(key="oil_pressure_system", name="机油压力", source="realtime", icon="mdi:oil", value_fn=_status_text("oil_pressure_system")),
    BydSensorDescription(key="engine_status", name="发动机", source="realtime", icon="mdi:engine", value_fn=_status_text("engine_status")),
    BydSensorDescription(key="ect", name="冷却液温度", source="realtime", icon="mdi:coolant-temperature", value_fn=_status_text("ect")),
    BydSensorDescription(key="tirepressure_system", name="胎压系统", source="realtime", icon="mdi:car-tire-alert", value_fn=_status_text("tirepressure_system")),
    # --- 车门 ---
    BydSensorDescription(key="left_front_door", name="左前门", source="realtime", icon="mdi:car-door", value_fn=_door_text("left_front_door")),
    BydSensorDescription(key="right_front_door", name="右前门", source="realtime", icon="mdi:car-door", value_fn=_door_text("right_front_door")),
    BydSensorDescription(key="left_rear_door", name="左后门", source="realtime", icon="mdi:car-door", value_fn=_door_text("left_rear_door")),
    BydSensorDescription(key="right_rear_door", name="右后门", source="realtime", icon="mdi:car-door", value_fn=_door_text("right_rear_door")),
    BydSensorDescription(key="trunk_lid", name="后备箱", source="realtime", icon="mdi:car-back", value_fn=_door_text("trunk_lid")),
    # --- 门锁 ---
    BydSensorDescription(key="left_front_door_lock", name="左前门锁", source="realtime", icon="mdi:lock", value_fn=_lock_text("left_front_door_lock")),
    BydSensorDescription(key="right_front_door_lock", name="右前门锁", source="realtime", icon="mdi:lock", value_fn=_lock_text("right_front_door_lock")),
    BydSensorDescription(key="left_rear_door_lock", name="左后门锁", source="realtime", icon="mdi:lock", value_fn=_lock_text("left_rear_door_lock")),
    BydSensorDescription(key="right_rear_door_lock", name="右后门锁", source="realtime", icon="mdi:lock", value_fn=_lock_text("right_rear_door_lock")),
    # --- 车窗 ---
    BydSensorDescription(key="left_front_window", name="左前窗", source="realtime", icon="mdi:car-door", value_fn=_window_text("left_front_window")),
    BydSensorDescription(key="right_front_window", name="右前窗", source="realtime", icon="mdi:car-door", value_fn=_window_text("right_front_window")),
    BydSensorDescription(key="right_rear_window", name="右后窗", source="realtime", icon="mdi:car-door", value_fn=_window_text("right_rear_window")),
    BydSensorDescription(key="left_rear_window", name="左后窗", source="realtime", icon="mdi:car-door", value_fn=_window_text("left_rear_window")),
    BydSensorDescription(key="skylight", name="天窗", source="realtime", icon="mdi:car-door", value_fn=_window_text("skylight")),
    # --- 轮胎状态 ---
    BydSensorDescription(key="left_front_tire_status", name="左前轮胎", source="realtime", icon="mdi:car-tire-alert", value_fn=_tire_status_text("left_front_tire_status")),
    BydSensorDescription(key="right_front_tire_status", name="右前轮胎", source="realtime", icon="mdi:car-tire-alert", value_fn=_tire_status_text("right_front_tire_status")),
    BydSensorDescription(key="left_rear_tire_status", name="左后轮胎", source="realtime", icon="mdi:car-tire-alert", value_fn=_tire_status_text("left_rear_tire_status")),
    BydSensorDescription(key="right_rear_tire_status", name="右后轮胎", source="realtime", icon="mdi:car-tire-alert", value_fn=_tire_status_text("right_rear_tire_status")),
    # --- 胎压 ---
    BydSensorDescription(key="left_front_tire_pressure", name="左前胎压", source="realtime", icon="mdi:car-tire-alert", native_unit_of_measurement=UnitOfPressure.KPA, suggested_display_precision=0),
    BydSensorDescription(key="right_front_tire_pressure", name="右前胎压", source="realtime", icon="mdi:car-tire-alert", native_unit_of_measurement=UnitOfPressure.KPA, suggested_display_precision=0),
    BydSensorDescription(key="left_rear_tire_pressure", name="左后胎压", source="realtime", icon="mdi:car-tire-alert", native_unit_of_measurement=UnitOfPressure.KPA, suggested_display_precision=0),
    BydSensorDescription(key="right_rear_tire_pressure", name="右后胎压", source="realtime", icon="mdi:car-tire-alert", native_unit_of_measurement=UnitOfPressure.KPA, suggested_display_precision=0),
    # --- 充电 ---
    BydSensorDescription(key="small_ui_smart_charge_tips", name="充电状态", source="realtime", icon="mdi:ev-station"),
    BydSensorDescription(key="charging_power", name="充电功率", source="realtime", icon="mdi:flash"),
    BydSensorDescription(key="remaining_hours", name="剩余充电小时", source="realtime", icon="mdi:clock-outline"),
    BydSensorDescription(key="remaining_minutes", name="剩余充电分钟", source="realtime", icon="mdi:clock-outline"),
    # --- 电量/里程 ---
    BydSensorDescription(key="elec_percent", name="电量", source="realtime", icon="mdi:battery", native_unit_of_measurement=PERCENTAGE, suggested_display_precision=0),
    BydSensorDescription(key="ev_endurance", name="纯电续航", source="realtime", icon="mdi:road-variant", native_unit_of_measurement=UnitOfLength.KILOMETERS, suggested_display_precision=0),
    BydSensorDescription(key="oil_percent", name="油量", source="realtime", icon="mdi:gas-station", native_unit_of_measurement=PERCENTAGE, suggested_display_precision=0),
    BydSensorDescription(key="oil_endurance", name="燃油续航", source="realtime", icon="mdi:gas-station", native_unit_of_measurement=UnitOfLength.KILOMETERS, suggested_display_precision=0),
    BydSensorDescription(key="hev_mileage", name="HEV里程", source="realtime", icon="mdi:counter", native_unit_of_measurement=UnitOfLength.KILOMETERS, suggested_display_precision=0),
    BydSensorDescription(key="total_mileage", name="总里程", source="realtime", icon="mdi:counter", native_unit_of_measurement=UnitOfLength.KILOMETERS, suggested_display_precision=0),
    # --- 能耗 ---
    BydSensorDescription(key="energy_consumption", name="最近能耗", source="realtime", icon="mdi:lightning-bolt", value_fn=_parse_numeric_string("energy_consumption")),
    BydSensorDescription(key="total_consumption", name="累计能耗", source="realtime", icon="mdi:lightning-bolt"),
    BydSensorDescription(key="total_consumption_en", name="累计能耗(英)", source="realtime", icon="mdi:lightning-bolt"),
    # --- GPS (原始数值) ---
    BydSensorDescription(key="gps_latitude", name="GPS纬度", source="gps", suggested_display_precision=6, icon="mdi:crosshairs-gps", use_gps_coordinator=True),
    BydSensorDescription(key="gps_longitude", name="GPS经度", source="gps", suggested_display_precision=6, icon="mdi:crosshairs-gps", use_gps_coordinator=True),
    # --- 时间戳 ---
    BydSensorDescription(key="last_updated", name="数据更新时间", source="realtime", device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:clock-outline"),
    BydSensorDescription(key="gps_last_updated", name="GPS更新时间", source="gps", device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:crosshairs-gps", use_gps_coordinator=True),
)


# =============================================
# GPS Sensor (uses BydGpsUpdateCoordinator directly)
# =============================================

class BydGpsSensor(CoordinatorEntity[BydGpsUpdateCoordinator], SensorEntity):
    """GPS sensor backed by BydGpsUpdateCoordinator."""

    _attr_has_entity_name = True
    entity_description: BydSensorDescription

    def __init__(
        self,
        coordinator: BydGpsUpdateCoordinator,
        vin: str,
        vehicle: Vehicle,
        description: BydSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._vehicle = vehicle
        self._attr_unique_id = f"{vin}_{description.source}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=get_vehicle_display(self._vehicle),
            manufacturer=self._vehicle.brand_name or "BYD",
            model=self._vehicle.model_name,
            serial_number=self._vin,
            hw_version=self._vehicle.tbox_version or None,
        )

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        data = self.coordinator.data
        return isinstance(data, GpsInfo) and data.latitude is not None and data.longitude is not None

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not isinstance(data, GpsInfo):
            return None
        key = self.entity_description.key
        if key == "gps_latitude":
            return data.latitude
        if key == "gps_longitude":
            return data.longitude
        if key == "gps_last_updated":
            val = data.gps_timestamp
            if isinstance(val, datetime):
                return val.replace(tzinfo=UTC) if val.tzinfo is None else val
            return val
        return None


# =============================================
# SETUP ENTRY
# =============================================

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BYD sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators: dict[str, BydDataUpdateCoordinator] = data["coordinators"]
    gps_coordinators = data.get("gps_coordinators", {})

    entities: list[SensorEntity] = []

    for vin, coordinator in coordinators.items():
        vehicle = coordinator.vehicle
        gps_coordinator = gps_coordinators.get(vin)

        for description in SENSOR_DESCRIPTIONS:
            if description.use_gps_coordinator:
                if gps_coordinator is not None:
                    entities.append(BydGpsSensor(gps_coordinator, vin, vehicle, description))
                continue
            entities.append(BydSensor(coordinator, vin, vehicle, description))

    async_add_entities(entities)


# Keys that read from Vehicle model (not realtime data)
_VEHICLE_INFO_KEYS = {"vin", "c_car_type", "auto_plate", "auto_out_color", "vehicle_image", "channel"}


class BydSensor(BydVehicleEntity, SensorEntity):
    """Representation of a BYD vehicle sensor."""

    _attr_has_entity_name = True
    entity_description: BydSensorDescription

    def __init__(
        self,
        coordinator: BydDataUpdateCoordinator | BydGpsUpdateCoordinator,
        vin: str,
        vehicle: Vehicle,
        description: BydSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._vin = vin
        self._vehicle = vehicle
        self._attr_unique_id = f"{vin}_{description.source}_{description.key}"
        self._last_native_value: Any | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_gps_direct(self) -> GpsInfo | None:
        """Get GPS data directly - works for both coordinator types."""
        data = self.coordinator.data
        if data is None:
            return None
        if isinstance(data, GpsInfo):
            return data
        return getattr(data, "gps", None)

    def _resolve_value(self) -> Any:
        """Extract the current value using the description's extraction logic."""
        key = self.entity_description.key

        # Timestamp sensors
        if key == "last_updated":
            realtime = self._get_realtime()
            if realtime is None:
                return None
            return _normalize_epoch(getattr(realtime, "timestamp", None))

        if key == "gps_last_updated":
            gps = self._get_gps_direct()
            if gps is None:
                return None
            return _normalize_epoch(getattr(gps, "gps_timestamp", None))

        # Vehicle info fields
        if key == "vin":
            return self._vehicle.vin or None
        if key == "c_car_type":
            # Try multiple sources for full model name
            realtime = self._get_realtime()
            if realtime is not None:
                val = getattr(realtime, "c_car_type", None)
                if val:
                    return val
            # Try raw dict from vehicle_info
            raw = getattr(self._vehicle, "raw", None)
            if isinstance(raw, dict):
                for k in ("cCarType", "outModelType", "modelName"):
                    v = raw.get(k)
                    if v and isinstance(v, str) and v.strip():
                        return v.strip()
            if self._vehicle.out_model_type:
                return self._vehicle.out_model_type
            return self._vehicle.model_name or None
        if key == "auto_plate":
            realtime = self._get_realtime()
            if realtime is not None:
                val = getattr(realtime, "auto_plate", None)
                if val:
                    return val
            raw = getattr(self._vehicle, "raw", None)
            if isinstance(raw, dict):
                v = raw.get("autoPlate")
                if v and isinstance(v, str) and v.strip():
                    return v.strip()
            return self._vehicle.auto_plate or None
        if key == "auto_out_color":
            realtime = self._get_realtime()
            if realtime is not None:
                val = getattr(realtime, "auto_out_color", None)
                if val:
                    return val
            raw = getattr(self._vehicle, "raw", None)
            if isinstance(raw, dict):
                v = raw.get("autoOutColor")
                if v and isinstance(v, str) and v.strip():
                    return v.strip()
            return self._vehicle.auto_out_color or None
        if key == "vehicle_image":
            raw = getattr(self._vehicle, "raw", None)
            if isinstance(raw, dict):
                v = raw.get("diFansVehicleImg")
                if v and isinstance(v, str) and v.strip():
                    return v.strip()
            return self._vehicle.pic_main_url or None
        if key == "channel":
            # channel from vehicle_info raw dict, translate to brand name
            _CHANNEL_MAP = {1: "王朝", 2: "海洋", 3: "腾势", 4: "方程豹", 5: "仰望"}
            ch = getattr(self._vehicle, "channel", None)
            if ch is not None:
                return _CHANNEL_MAP.get(ch, str(ch))
            # Fallback: try raw dict
            raw = getattr(self._vehicle, "raw", None)
            if isinstance(raw, dict):
                ch = raw.get("channel") or raw.get("appChannel")
                if ch is not None:
                    ch = int(ch) if isinstance(ch, str) and ch.isdigit() else ch
                    return _CHANNEL_MAP.get(ch, str(ch)) if isinstance(ch, int) else str(ch)
            return None

        # GPS fields
        if key == "gps_latitude":
            gps = self._get_gps_direct()
            return gps.latitude if gps is not None else None
        if key == "gps_longitude":
            gps = self._get_gps_direct()
            return gps.longitude if gps is not None else None

        # Standard path: get source object and apply value_fn or direct attr
        obj = self._get_source_obj(self.entity_description.source)
        if obj is None:
            return None

        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(obj)

        attr = self.entity_description.attr_key or key
        value = getattr(obj, attr, None)
        # For enum values, return the raw int
        enum_value = getattr(value, "value", None)
        if isinstance(enum_value, int):
            return enum_value
        return value

    def _resolve_validated_value(self) -> Any:
        """Resolve sensor value and apply optional per-entity validation."""
        value = self._resolve_value()
        validator = self.entity_description.validator_fn
        if validator is not None:
            value = validator(self._last_native_value, value)
        if value is not None:
            self._last_native_value = value
        return value

    # ------------------------------------------------------------------
    # Entity properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True when the coordinator has data for this source."""
        key = self.entity_description.key
        if key in ("gps_latitude", "gps_longitude", "gps_last_updated"):
            gps = self._get_gps_direct()
            return gps is not None and gps.latitude is not None and gps.longitude is not None
        if key in ("last_updated",):
            return self._resolve_value() is not None
        if key in _VEHICLE_INFO_KEYS:
            return self.coordinator.last_update_success
        if not super().available:
            return False
        return self._get_source_obj(self.entity_description.source) is not None

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self._resolve_validated_value()