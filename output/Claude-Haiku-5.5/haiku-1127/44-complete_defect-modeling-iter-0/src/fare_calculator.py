"""Beijing Subway fare calculation based on the distance-tier fare structure.

Fare structure (distances are rounded up to whole kilometers):
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    > 32 km   : 6 yuan + 1 yuan for every started 20 km beyond 32 km
"""

import math
from dataclasses import dataclass
from typing import Optional

# Average operating speed used for time estimates (km/h).
AVERAGE_SPEED_KMH = 35.0
# Fixed boarding time added to every trip (minutes).
BOARDING_TIME_MIN = 3.0
# Extra time per transfer (minutes).
TRANSFER_TIME_MIN = 5.0


class FareCalculationError(ValueError):
    """Raised when a fare or time cannot be calculated from the given input."""


@dataclass(frozen=True)
class FareRule:
    """One tier of the fare table.

    Attributes:
        min_distance_km: lower bound of the tier (exclusive for tiers after the first).
        max_distance_km: upper bound (inclusive) or None for open-ended tiers.
        fare_yuan: base fare for the tier.
        extension_step_km: for open-ended tiers, the km length per extra yuan (0 if none).
    """

    min_distance_km: float
    max_distance_km: Optional[float]
    fare_yuan: int
    extension_step_km: int = 0


FARE_RULES = (
    FareRule(0, 6, 3),
    FareRule(6, 12, 4),
    FareRule(12, 22, 5),
    FareRule(22, 32, 6),
    FareRule(32, None, 6, 20),
)


@dataclass(frozen=True)
class Fare:
    """Result of a fare calculation."""

    amount_yuan: int
    distance_km: float
    rounded_up_distance_km: int


def _validate_distance(distance):
    """Ensure ``distance`` (meters) is a finite, non-negative number."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError("distance must be a number of meters")
    if not math.isfinite(distance) or distance < 0:
        raise FareCalculationError("distance must be a finite, non-negative number")


def rounded_up_distance_km(distance):
    """Convert meters to kilometers rounded up to the next whole kilometer."""
    _validate_distance(distance)
    return int(math.ceil(distance / 1000.0 - 1e-9))


def _fare_for_km(km):
    """Look up the fare for a whole-kilometer distance using the tier table."""
    for rule in FARE_RULES:
        if rule.max_distance_km is None or km <= rule.max_distance_km:
            if rule.extension_step_km > 0:
                extra = math.ceil((km - rule.min_distance_km) / rule.extension_step_km)
                return rule.fare_yuan + max(0, extra)
            return rule.fare_yuan
    raise FareCalculationError("no fare rule matches distance {} km".format(km))


def Sum_money(distance):
    """Return the fare in yuan (int) for a trip of ``distance`` meters."""
    return _fare_for_km(rounded_up_distance_km(distance))


def calculate_fare(distance):
    """Return a ``Fare`` object describing the fare for ``distance`` meters."""
    km = rounded_up_distance_km(distance)
    return Fare(
        amount_yuan=_fare_for_km(km),
        distance_km=distance / 1000.0,
        rounded_up_distance_km=km,
    )


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: total distance in meters.
        transfer_count: number of transfers on the trip.

    Returns:
        Estimated travel time in minutes (float).
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise FareCalculationError("transfer_count must be a non-negative integer")
    riding = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return riding + BOARDING_TIME_MIN + transfer_count * TRANSFER_TIME_MIN
