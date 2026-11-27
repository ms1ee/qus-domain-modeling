"""Fare and travel-time calculation based on the Beijing Subway fare structure.

Fare tiers (distance in meters):
    [0, 6000)         -> 3 yuan
    [6000, 12000)     -> 4 yuan
    [12000, 22000)    -> 5 yuan
    [22000, 32000)    -> 6 yuan
    >= 32000          -> 7 yuan, plus 1 yuan for every further 20 km (floor-based)
"""

import math

# (upper bound exclusive in meters, fare in yuan) for the basic and progressive tiers.
FARE_TIERS = ((6000, 3), (12000, 4), (22000, 5), (32000, 6))
EXTENDED_THRESHOLD_METERS = 32000
EXTENDED_STEP_METERS = 20000
EXTENDED_BASE_FARE = 7

AVERAGE_SPEED_KMH = 35.0        # average in-service speed used for time estimates
TRANSFER_TIME_MINUTES = 5.0     # walking and waiting time per transfer
BOARDING_TIME_MINUTES = 2.0     # fixed boarding overhead per trip


def _validate_distance(distance) -> float:
    """Ensure ``distance`` is a finite, non-negative real number in meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("Distance must be finite")
    if distance < 0:
        raise ValueError("Distance must be non-negative")
    return distance


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a journey of ``distance`` meters.

    Boundary values follow the tier table: 6000 m -> 4 yuan, 12000 m -> 5 yuan,
    22000 m -> 6 yuan, 32000 m -> 7 yuan.
    """
    value = _validate_distance(distance)
    for upper_bound, fare in FARE_TIERS:
        if value < upper_bound:
            return fare
    extra_steps = (value - EXTENDED_THRESHOLD_METERS) // EXTENDED_STEP_METERS
    return EXTENDED_BASE_FARE + int(extra_steps)


def describe_fare_tier(distance) -> str:
    """Return a human-readable description of the fare tier for ``distance`` meters."""
    value = _validate_distance(distance)
    if value < 6000:
        return "Basic tier (0-6 km)"
    if value < 12000:
        return "Progressive tier (6-12 km)"
    if value < 22000:
        return "Progressive tier (12-22 km)"
    if value < 32000:
        return "Progressive tier (22-32 km)"
    return "Extended tier (over 32 km)"


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes from distance (meters) and transfer count.

    The estimate is in-vehicle time at an average speed, plus a fixed boarding
    overhead and a fixed time penalty per transfer.
    """
    value = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("Transfer count must be a non-negative integer")
    travel_minutes = (value / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = travel_minutes + BOARDING_TIME_MINUTES + transfer_count * TRANSFER_TIME_MINUTES
    return float(round(total, 1))
