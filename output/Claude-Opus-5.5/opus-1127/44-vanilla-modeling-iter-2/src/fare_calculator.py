"""
Fare calculation based on the Beijing Subway fare structure.

Tiers (left-closed, right-open intervals, distances in meters):

* [0, 6000)      -> 3 yuan   (basic tier)
* [6000, 12000)  -> 4 yuan
* [12000, 22000) -> 5 yuan
* [22000, 32000) -> 6 yuan
* >= 32000       -> 7 yuan plus 1 yuan for every additional full 20 km
                    (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Fractional distances are rounded up (ceiling) to whole meters first.
"""

import math
from dataclasses import dataclass
from typing import Optional

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


@dataclass(frozen=True)
class FareTier:
    name: str
    min_distance: int
    max_distance: Optional[int]
    fare: int


#: Distance segment -> fare mapping for the bounded tiers.
FARE_TIERS = (
    FareTier("Basic", 0, 6000, 3),
    FareTier("Progressive", 6000, 12000, 4),
    FareTier("Progressive", 12000, 22000, 5),
    FareTier("Progressive", 22000, 32000, 6),
)

EXTENDED_START_DISTANCE = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1


@dataclass(frozen=True)
class FareStructure:
    tiers: tuple = FARE_TIERS
    extended_start_distance: int = EXTENDED_START_DISTANCE
    extended_base_fare: int = EXTENDED_BASE_FARE
    extended_increment_distance: int = EXTENDED_INCREMENT_DISTANCE
    extended_increment_fare: int = EXTENDED_INCREMENT_FARE


@dataclass(frozen=True)
class FareResult:
    distance: int
    fare: int


class FareCalculationError(ValueError, TypeError):
    """Raised for invalid distance input (non-numeric, negative, NaN, infinite)."""


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FareCalculationError(f"{name} must be a number, got {type(value).__name__}")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise FareCalculationError(f"{name} must be a finite number")
    if value < 0:
        raise FareCalculationError(f"{name} must be non-negative, got {value}")


def Sum_money(distance):
    """Return the fare (yuan) for a travel distance given in meters."""
    _validate_number(distance, "Distance")
    meters = int(math.ceil(distance))
    for tier in FARE_TIERS:
        if tier.min_distance <= meters < tier.max_distance:
            return tier.fare
    extra = (meters - EXTENDED_START_DISTANCE) // EXTENDED_INCREMENT_DISTANCE
    return EXTENDED_BASE_FARE + extra * EXTENDED_INCREMENT_FARE


def calculate_fare(distance):
    """Return a :class:`FareResult` for a distance in meters."""
    fare = Sum_money(distance)
    return FareResult(distance=int(math.ceil(distance)), fare=fare)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes.

    About 1.5 minutes per kilometer plus about 5 minutes per transfer.

    :param distance: distance in meters
    :param transfer_count: number of transfers
    """
    _validate_number(distance, "Distance")
    _validate_number(transfer_count, "Transfer count")
    return float(distance) / 1000.0 * MINUTES_PER_KM + float(transfer_count) * MINUTES_PER_TRANSFER
