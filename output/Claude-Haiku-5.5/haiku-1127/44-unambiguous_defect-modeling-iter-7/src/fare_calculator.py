"""
Fare calculation for the Beijing Subway.

Fare structure (distances in meters):
  * 0      - 6000   : 3 yuan
  * 6000   - 12000  : 4 yuan
  * 12000  - 22000  : 5 yuan
  * 22000  - 32000  : 6 yuan
  * >= 32000        : 7 yuan, plus 1 yuan for every further 20 km
Boundary values belong to the higher tier (e.g. exactly 6000 m costs 4 yuan).
Fractional meters are rounded up before tier lookup.
"""

import math
from dataclasses import dataclass
from typing import Optional

EXTENDED_STEP_METERS = 20000.0
AVERAGE_SPEED_KMH = 35.0
BASE_TRAVEL_MINUTES = 2.0
MINUTES_PER_TRANSFER = 4.0


@dataclass(frozen=True)
class FareTier:
    """
    One fare tier.

    Attributes:
        name: Human-readable tier name.
        min_distance_m: Inclusive lower bound in meters.
        max_distance_m: Exclusive upper bound in meters, None for the extended tier.
        base_fare: Fare (yuan) at the lower bound of the tier.
        increment_per_km: Fare increment per kilometer (informational; the
                          extended tier increments 1 yuan per 20 km).
    """
    name: str
    min_distance_m: float
    max_distance_m: Optional[float]
    base_fare: int
    increment_per_km: float


FARE_TIERS = (
    FareTier("Basic", 0.0, 6000.0, 3, 0.0),
    FareTier("Progressive 6-12 km", 6000.0, 12000.0, 4, 0.0),
    FareTier("Progressive 12-22 km", 12000.0, 22000.0, 5, 0.0),
    FareTier("Progressive 22-32 km", 22000.0, 32000.0, 6, 0.0),
    FareTier("Extended over 32 km", 32000.0, None, 7, 1.0 / 20.0),
)


def _validate_distance(distance):
    """Validate a distance in meters and return it as a float."""
    if distance is None or isinstance(distance, bool):
        raise ValueError("distance must be a number of meters")
    try:
        value = float(distance)
    except (TypeError, ValueError):
        raise ValueError("distance must be a number of meters")
    if math.isnan(value) or math.isinf(value):
        raise ValueError("distance must be a finite number")
    if value < 0:
        raise ValueError("distance must not be negative")
    return value


def _tier_for(meters):
    """Return the FareTier that applies to ``meters`` (already rounded up)."""
    for tier in FARE_TIERS:
        if tier.max_distance_m is None or meters < tier.max_distance_m:
            return tier
    return FARE_TIERS[-1]


def Sum_money(distance):
    """
    Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters.

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is invalid (negative, non-numeric, NaN, infinite).
    """
    meters = math.ceil(_validate_distance(distance))
    tier = _tier_for(meters)
    if tier.max_distance_m is None:
        extra_steps = int((meters - tier.min_distance_m) // EXTENDED_STEP_METERS)
        return tier.base_fare + extra_steps
    return tier.base_fare


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate the travel time of a journey.

    The estimate is the in-train time at an average speed of 35 km/h, plus a
    fixed base time for boarding and alighting, plus a fixed time per transfer.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes (one decimal place).

    Raises:
        ValueError: If the distance or transfer count is invalid.
    """
    meters = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) \
            or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    ride_minutes = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = ride_minutes + BASE_TRAVEL_MINUTES + MINUTES_PER_TRANSFER * transfer_count
    return round(total, 1)


class FareCalculator:
    """
    Object-oriented wrapper around the fare functions.

    Attributes:
        rounding_rule: Description of how fractional meters are rounded.
    """

    def __init__(self):
        self.rounding_rule = "round_up_to_meter"

    def fare_for(self, distance):
        """Return the fare in yuan for ``distance`` meters."""
        return Sum_money(distance)

    def tier_for(self, distance):
        """Return the FareTier that applies to ``distance`` meters."""
        return _tier_for(math.ceil(_validate_distance(distance)))

    def tiers(self):
        """Return all configured fare tiers."""
        return list(FARE_TIERS)
