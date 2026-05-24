"""Capability namespace classes for BydCar.

Each capability encapsulates a group of related vehicle commands with
their associated projection specifications.
"""

from pybyd_china._capabilities.battery_heat import BatteryHeatCapability
from pybyd_china._capabilities.finder import FinderCapability
from pybyd_china._capabilities.hvac import HvacCapability
from pybyd_china._capabilities.lock import LockCapability
from pybyd_china._capabilities.seat import SeatCapability, SeatLevel, SeatPosition
from pybyd_china._capabilities.steering import SteeringCapability
from pybyd_china._capabilities.windows import WindowsCapability

__all__ = [
    "BatteryHeatCapability",
    "FinderCapability",
    "HvacCapability",
    "LockCapability",
    "SeatCapability",
    "SeatLevel",
    "SeatPosition",
    "SteeringCapability",
    "WindowsCapability",
]
