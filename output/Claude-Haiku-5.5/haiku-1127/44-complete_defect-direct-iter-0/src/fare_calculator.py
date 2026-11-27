"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distance in kilometres, rounded up to the next whole km):
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    beyond 32 km: +1 yuan for every further 20 km (or part thereof)
"""

import math
from typing import Any

# (inclusive upper bound in kilometres, fare in yuan)
FARE_TIERS = ((6, 3), (12, 4), (22, 5), (32, 6))
EXTENSION_THRESHOLD_KM = 32
EXTENSION_STEP_KM = 20
EXTENSION_STEP_FARE = 1

AVERAGE_SPEED_KMH = 35.0      # average operating speed including stops
MINUTES_PER_TRANSFER = 5.0    # walking and waiting time per line change


def _validate_distance(distance: Any) -> float:
    """Convert a distance in meters to float, validating its value."""
    if isinstance(distance, bool):
        raise TypeError("Distance must be a number of meters, not a bool")
    try:
        meters = float(distance)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"Distance must be a number of meters, got {distance!r}") from exc
    if math.isnan(meters) or math.isinf(meters):
        raise ValueError("Distance must be a finite number")
    if meters < 0:
        raise ValueError("Distance must not be negative")
    return meters


def Sum_money(distance: Any) -> int:
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters.

    Returns:
        Fare in yuan (integer).
    """
    meters = _validate_distance(distance)
    km = math.ceil(meters / 1000.0)  # ceiling rounding of fractional kilometres
    for upper, fare in FARE_TIERS:
        if km <= upper:
            return fare
    extra_steps = math.ceil((km - EXTENSION_THRESHOLD_KM) / EXTENSION_STEP_KM)
    return FARE_TIERS[-1][1] + extra_steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance: Any, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line changes on the route.

    Returns:
        Estimated travel time in minutes, rounded to one decimal place.
    """
    meters = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    travel_minutes = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(travel_minutes + transfer_count * MINUTES_PER_TRANSFER, 1)
