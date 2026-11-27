"""Beijing Subway fare calculation.

Fare structure:
    0-6 km: 3 yuan
    6-12 km: 4 yuan
    12-22 km: 5 yuan
    22-32 km: 6 yuan
    beyond 32 km: 6 yuan plus 1 yuan for every additional 20 km

Distances are rounded up to whole kilometers before applying the tiers,
so any fractional kilometer counts as a full kilometer (ceiling rounding).
"""

import math
from dataclasses import dataclass

from models import Fare

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 4.0


@dataclass(frozen=True)
class FareRule:
    """A distance tier of the fare structure.

    Attributes:
        min_distance_km: Lower bound of the tier (exclusive, except for the first tier).
        max_distance_km: Upper bound of the tier (inclusive).
        fare_yuan: Fare in yuan for the tier.
        increment_km: Distance per extra fare step (0 for fixed tiers).
    """

    min_distance_km: float
    max_distance_km: float
    fare_yuan: int
    increment_km: float = 0.0


FARE_RULES = (
    FareRule(0.0, 6.0, 3),
    FareRule(6.0, 12.0, 4),
    FareRule(12.0, 22.0, 5),
    FareRule(22.0, 32.0, 6),
)

# Extension beyond the last fixed tier: +1 yuan for every 20 km.
EXTENSION_BASE_KM = 32.0
EXTENSION_INCREMENT_KM = 20
EXTENSION_STEP_YUAN = 1


def _validate_distance(distance) -> float:
    """Validate a distance in meters and return it as float."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number of meters")
    value = float(distance)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Distance must be a finite number")
    if value < 0:
        raise ValueError("Distance cannot be negative")
    return value


def rounded_distance_km(distance: float) -> int:
    """Return the distance in meters rounded up to whole kilometers."""
    value = _validate_distance(distance)
    return int(math.ceil(round(value / 1000.0, 9)))


def Sum_money(distance: float) -> int:
    """Calculate the subway fare in yuan for a distance given in meters.

    Args:
        distance: Travelled distance in meters.

    Returns:
        The fare in yuan (integer).
    """
    km = rounded_distance_km(distance)
    for rule in FARE_RULES:
        if km <= rule.max_distance_km:
            return rule.fare_yuan
    last_rule = FARE_RULES[-1]
    extra_km = km - EXTENSION_BASE_KM
    steps = -(-int(extra_km) // EXTENSION_INCREMENT_KM)  # ceiling division
    return last_rule.fare_yuan + steps * EXTENSION_STEP_YUAN


def calculate_fare(distance: float) -> Fare:
    """Return a ``Fare`` object describing the fare for a distance in meters."""
    return Fare(amount_yuan=Sum_money(distance),
                rounded_distance_km=float(rounded_distance_km(distance)))


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated travel time in minutes, including transfer time.
    """
    value = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    travel_minutes = (value / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return travel_minutes + transfer_count * TRANSFER_TIME_MINUTES
