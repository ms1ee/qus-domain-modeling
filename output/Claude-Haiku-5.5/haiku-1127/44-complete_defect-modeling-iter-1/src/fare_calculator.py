"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distances are rounded up to whole kilometers):
    0-6 km    -> 3 yuan
    6-12 km   -> 4 yuan
    12-22 km  -> 5 yuan
    22-32 km  -> 6 yuan
    > 32 km   -> 6 yuan + 1 yuan for every started 20 km beyond 32 km
"""

import math
from typing import List, Tuple

# (upper bound in whole km inclusive, fare in yuan), in ascending order.
FARE_TIERS: List[Tuple[int, int]] = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]

# Distance beyond which the extension rule applies.
EXTENSION_THRESHOLD_KM = 32
# Length of each extension step in kilometers.
EXTENSION_STEP_KM = 20
# Fare added per extension step in yuan.
EXTENSION_FARE_STEP = 1

# Average in-train speed used for time estimates (km/h).
AVERAGE_SPEED_KMH = 35.0
# Time cost per transfer including walking and waiting (minutes).
TRANSFER_TIME_MIN = 5.0
# Fixed boarding time for every trip (minutes).
BOARDING_TIME_MIN = 3.0


def _validate_non_negative_number(value, name: str) -> None:
    """Raise if ``value`` is not a finite, non-negative real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def Sum_money(distance) -> int:
    """Compute the subway fare in yuan for a trip of ``distance`` meters.

    The distance is converted to kilometers and rounded up (ceiling), so any
    fraction of a kilometer counts as a full kilometer for tier selection.

    Args:
        distance: Travel distance in meters.

    Returns:
        Fare in yuan as an integer.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative or not finite.
    """
    _validate_non_negative_number(distance, "distance")
    km = math.ceil(distance / 1000.0)

    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    extra_km = km - EXTENSION_THRESHOLD_KM
    steps = math.ceil(extra_km / EXTENSION_STEP_KM)
    base_fare = FARE_TIERS[-1][1]
    return base_fare + steps * EXTENSION_FARE_STEP


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate the travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of line changes.

    Returns:
        Estimated time in minutes, rounded to one decimal place.

    Raises:
        TypeError: If the arguments are not numbers.
        ValueError: If the arguments are negative or not finite.
    """
    _validate_non_negative_number(distance, "distance")
    _validate_non_negative_number(transfer_count, "transfer_count")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = travel_minutes + transfer_count * TRANSFER_TIME_MIN + BOARDING_TIME_MIN
    return round(total, 1)
