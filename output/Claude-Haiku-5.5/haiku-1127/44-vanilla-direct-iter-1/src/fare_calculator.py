"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distances are left-closed, right-open intervals, so a boundary
value enters the next tier):

* 0 to 6 km: 3 yuan
* 6 to 12 km: 4 yuan
* 12 to 22 km: 5 yuan
* 22 to 32 km: 6 yuan
* 32 km and over: 7 yuan, plus 1 yuan for every additional 20 km
  (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Fractional meters are rounded up (ceiling) before the tier is determined.
"""

import math

# Fare tiers as (lower bound inclusive, upper bound exclusive, fare in yuan), in meters.
FARE_TIERS = (
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
)
EXTENDED_START_M = 32000
EXTENDED_STEP_M = 20000
EXTENDED_BASE_FARE = 7

# Travel-time model used for estimates.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _normalize_distance(distance):
    """Validate a distance in meters and round it up to a whole meter."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number of meters, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    return math.ceil(distance)


def Sum_money(distance):
    """Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters (int or float; fractions are
            rounded up).

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative or not finite.
    """
    meters = _normalize_distance(distance)
    for lower, upper, fare in FARE_TIERS:
        if lower <= meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of line transfers.

    Returns:
        float: Estimated time in minutes (about 1.5 min/km plus 5 min per transfer).

    Raises:
        TypeError: If the inputs are not numbers.
        ValueError: If the inputs are negative or not finite.
    """
    meters = _normalize_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count cannot be negative")
    return (meters / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
