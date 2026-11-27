"""Beijing Subway fare and travel-time calculations.

Fare structure (distance in meters, fractional meters rounded up):
    0 - 6 km        : 3 yuan
    6 - 12 km       : 4 yuan
    12 - 22 km      : 5 yuan
    22 - 32 km      : 6 yuan
    over 32 km      : 7 yuan, plus 1 yuan for every further 20 km
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from errors import FareError

AVERAGE_SPEED_KMH = 35.0  # average operating speed used for time estimates
BOARDING_OVERHEAD_MIN = 2.0  # fixed time for entering and leaving stations
TRANSFER_TIME_MIN = 5.0  # time spent per line change


@dataclass(frozen=True)
class FareTier:
    """One band of the distance-based fare table.

    Attributes:
        min_distance: Lower bound in meters (inclusive).
        max_distance: Upper bound in meters (exclusive), or ``None`` for an open tier.
        base_fare: Fare in yuan at the lower bound of the tier.
        increment_per_km: Extra yuan per kilometre beyond ``min_distance``,
            applied with floor rounding (0.05 means 1 yuan per 20 km).
    """

    min_distance: float
    max_distance: float | None
    base_fare: int
    increment_per_km: float


FARE_TIERS: tuple[FareTier, ...] = (
    FareTier(0.0, 6000.0, 3, 0.0),
    FareTier(6000.0, 12000.0, 4, 0.0),
    FareTier(12000.0, 22000.0, 5, 0.0),
    FareTier(22000.0, 32000.0, 6, 0.0),
    FareTier(32000.0, None, 7, 0.05),
)


def _validate_distance(distance) -> float:
    """Convert a distance in meters to a finite non-negative float.

    Raises:
        FareError: If the value is not a finite, non-negative number.
    """
    if isinstance(distance, bool):
        raise FareError("distance must be a number")
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise FareError(f"distance must be a number, got {distance!r}") from exc
    if not math.isfinite(value):
        raise FareError("distance must be a finite number")
    if value < 0:
        raise FareError("distance must not be negative")
    return value


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Travelled distance in meters. Fractional meters are rounded up.

    Returns:
        The fare as an integer number of yuan.

    Raises:
        FareError: If the distance is invalid.
    """
    meters = _validate_distance(distance)
    meters = math.ceil(meters - 1e-9)  # round fractional meters up

    for tier in FARE_TIERS:
        if tier.max_distance is None or meters < tier.max_distance:
            extra = 0
            if tier.increment_per_km:
                kilometres_over = (meters - tier.min_distance) / 1000.0
                extra = math.floor(kilometres_over * tier.increment_per_km + 1e-9)
            return tier.base_fare + int(extra)
    # Unreachable because the last tier is open-ended.
    raise FareError("no fare tier matches the distance")


def calculate_estimated_time(distance, transfer_count: int) -> float:
    """Estimate the travel time in minutes.

    The estimate combines riding time at an average speed, a fixed boarding
    overhead, and a fixed penalty for every line change.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line changes along the route.

    Returns:
        Estimated time in minutes, rounded to one decimal place.

    Raises:
        FareError: If the distance or transfer count is invalid.
    """
    meters = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise FareError("transfer_count must be a non-negative integer")
    riding_minutes = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = riding_minutes + BOARDING_OVERHEAD_MIN + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
