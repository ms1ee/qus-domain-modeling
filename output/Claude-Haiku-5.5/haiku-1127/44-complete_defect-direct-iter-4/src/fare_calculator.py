"""Fare and travel-time calculation for Beijing Subway trips."""

import math

# Fare tiers: (upper bound in whole kilometers inclusive, fare in yuan).
# 0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan.
FARE_TIERS = ((6, 3), (12, 4), (22, 5), (32, 6))
BASE_MAX_KM = FARE_TIERS[-1][0]
BASE_MAX_FARE = FARE_TIERS[-1][1]

# Beyond 32 km: +1 yuan for every additional 20 km (or part thereof).
EXTENSION_STEP_KM = 20
EXTENSION_STEP_FARE = 1

# Travel-time model.
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MIN = 5.0
BOARDING_TIME_MIN = 2.0


class FareCalculationError(Exception):
    """Raised when the fare cannot be computed for the given input."""


def Sum_money(distance: float) -> int:
    """Compute the subway fare in yuan for a trip of ``distance`` meters.

    Fractional kilometers are rounded up (ceiling), so 6.001 km is charged
    as 7 km.

    Args:
        distance: travelled distance in meters (non-negative).

    Returns:
        The fare in whole yuan.

    Raises:
        FareCalculationError: if the distance is not a valid non-negative number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError(f"Distance must be a number, got {distance!r}")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise FareCalculationError(f"Distance must be a finite non-negative value, got {distance}")

    # Round to 9 decimals first to avoid floating point noise such as 6000.0000000001.
    km = math.ceil(round(distance / 1000.0, 9))
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    extra_km = km - BASE_MAX_KM
    extra_steps = math.ceil(extra_km / EXTENSION_STEP_KM)
    return BASE_MAX_FARE + extra_steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate the travel time in minutes.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line transfers on the route.

    Returns:
        Estimated time in minutes, rounded to one decimal place.

    Raises:
        ValueError: if the inputs are negative.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    riding_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = riding_minutes + transfer_count * TRANSFER_TIME_MIN + BOARDING_TIME_MIN
    return round(total, 1)
