"""Data models for BYD API responses."""

from pybyd_china._constants import VALID_CLIMATE_DURATIONS, minutes_to_time_span
from pybyd_china.models._base import BydBaseModel, BydEnum, BydTimestamp, parse_byd_timestamp
from pybyd_china.models.charging import ChargingStatus
from pybyd_china.models.command_gating import CommandGateRule, CommandGateVerdict
from pybyd_china.models.control import (
    BatteryHeatParams,
    ClimateScheduleParams,
    ClimateStartParams,
    CommandAck,
    CommandAckDiagnostics,
    CommandAckEvent,
    CommandLifecycleEvent,
    CommandLifecycleStatus,
    ControlState,
    RemoteCommand,
    RemoteControlResult,
    SeatClimateParams,
    VerifyControlPasswordResponse,
)
from pybyd_china.models.energy import EnergyConsumption
from pybyd_china.models.gps import GpsInfo
from pybyd_china.models.hvac import HvacStatus, celsius_to_scale
from pybyd_china.models.latest_config import LatestConfigFunction, VehicleCapabilities, VehicleLatestConfig
from pybyd_china.models.push_notification import PushNotificationState
from pybyd_china.models.realtime import (
    AirCirculationMode,
    ChargingState,
    ConnectState,
    DoorOpenState,
    LockState,
    OnlineState,
    PowerGear,
    SeatHeatVentState,
    StearingWheelHeat,
    TirePressureUnit,
    VehicleRealtimeData,
    VehicleState,
    WindowState,
)
from pybyd_china.models.smart_charging import SmartChargingSchedule
from pybyd_china.models.token import AuthToken
from pybyd_china.models.vehicle import EmpowerRange, Vehicle

__all__ = [
    "AirCirculationMode",
    "AuthToken",
    "BatteryHeatParams",
    "BydBaseModel",
    "BydEnum",
    "BydTimestamp",
    "ChargingState",
    "ChargingStatus",
    "CommandGateRule",
    "CommandGateVerdict",
    "ClimateScheduleParams",
    "ClimateStartParams",
    "CommandAck",
    "CommandAckDiagnostics",
    "CommandAckEvent",
    "CommandLifecycleEvent",
    "CommandLifecycleStatus",
    "ConnectState",
    "ControlState",
    "DoorOpenState",
    "EmpowerRange",
    "EnergyConsumption",
    "GpsInfo",
    "HvacStatus",
    "LatestConfigFunction",
    "LockState",
    "OnlineState",
    "PowerGear",
    "PushNotificationState",
    "RemoteCommand",
    "RemoteControlResult",
    "SeatClimateParams",
    "SeatHeatVentState",
    "SmartChargingSchedule",
    "StearingWheelHeat",
    "TirePressureUnit",
    "VALID_CLIMATE_DURATIONS",
    "VehicleCapabilities",
    "Vehicle",
    "VehicleLatestConfig",
    "VehicleRealtimeData",
    "VehicleState",
    "VerifyControlPasswordResponse",
    "WindowState",
    "celsius_to_scale",
    "minutes_to_time_span",
    "parse_byd_timestamp",
]
