"""pybyd - Async Python client for BYD vehicle telemetry API."""

from importlib.metadata import PackageNotFoundError, version

from pybyd_china._capabilities.seat import SeatLevel, SeatPosition
from pybyd_china._state_engine import VehicleSnapshot
from pybyd_china.car import BydCar
from pybyd_china.client import BydClient
from pybyd_china.config import BydConfig, DeviceProfile
from pybyd_china.exceptions import (
    BydApiError,
    BydAuthenticationError,
    BydControlPasswordError,
    BydDataUnavailableError,
    BydEndpointNotSupportedError,
    BydError,
    BydRateLimitError,
    BydRemoteControlError,
    BydSessionExpiredError,
    BydTransportError,
)
from pybyd_china.models import (
    VALID_CLIMATE_DURATIONS,
    ChargingStatus,
    CommandAckEvent,
    CommandLifecycleEvent,
    DoorOpenState,
    EnergyConsumption,
    GpsInfo,
    HvacStatus,
    SeatHeatVentState,
    TirePressureUnit,
    Vehicle,
    VehicleCapabilities,
    VehicleLatestConfig,
    VehicleRealtimeData,
    WindowState,
    minutes_to_time_span,
)

try:
    __version__ = version("pybyd_china")
except PackageNotFoundError:
    __version__ = "0+local"

__all__ = [
    "__version__",
    "BydApiError",
    "BydAuthenticationError",
    "BydCar",
    "ChargingStatus",
    "BydClient",
    "BydConfig",
    "BydControlPasswordError",
    "BydDataUnavailableError",
    "BydEndpointNotSupportedError",
    "BydError",
    "BydRateLimitError",
    "BydRemoteControlError",
    "BydSessionExpiredError",
    "BydTransportError",
    "CommandAckEvent",
    "CommandLifecycleEvent",
    "DeviceProfile",
    "DoorOpenState",
    "EnergyConsumption",
    "GpsInfo",
    "HvacStatus",
    "SeatHeatVentState",
    "SeatLevel",
    "SeatPosition",
    "TirePressureUnit",
    "VALID_CLIMATE_DURATIONS",
    "VehicleCapabilities",
    "Vehicle",
    "VehicleLatestConfig",
    "VehicleRealtimeData",
    "VehicleSnapshot",
    "WindowState",
    "minutes_to_time_span",
]
