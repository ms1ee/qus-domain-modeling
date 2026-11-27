"""Fare calculation based on the Beijing Subway fare structure.

Fare tiers (left-closed, right-open intervals, distances in meters after
ceiling rounding):
    [0, 6000)          -> 3 yuan
    [6000, 12000)      -> 4 yuan
    [12000, 22000)     -> 5 yuan
    [22000, 32000)     -> 6 yuan
    [32000, 52000)     -> 7 yuan
    [52000, 72000)     -> 8 yuan
    ... +1 yuan for every additional 20 km beyond 32 km.
"""

import math

# (exclusive upper bound in meters, fare in yuan) for the basic and progressive tiers.
BASE_FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)

EXTENDED_START_M = 32000      # extended tier starts at 32 km
EXTENDED_STEP_M = 20000       # every 20 km beyond 32 km adds 1 yuan
EXTENDED_BASE_FARE = 7        # fare for [32 km, 52 km)

# Estimated travel time parameters.
AVERAGE_MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _validate_distance_value(distance):
    """Validate a numeric distance in meters and return it as a float."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number of meters, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance must not be negative")
    return float(distance)


def _to_whole_meters(distance):
    """Apply ceiling rounding to a distance in meters (fractional meters round up)."""
    _validate_distance_value(distance)
    return math.ceil(distance)


def Sum_money(distance):
    """Compute the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float). Fractional
            meters are rounded up before the tier lookup.

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative or not finite.
    """
    meters = _to_whole_meters(distance)
    for upper_bound, fare in BASE_FARE_TIERS:
        if meters < upper_bound:
            return fare
    # meters >= 32 km: extended tier, +1 yuan per 20 km.
    steps = (meters - EXTENDED_START_M) // EXTENDED_STEP_M
    return EXTENDED_BASE_FARE + steps


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line transfers (non-negative integer).

    Returns:
        float: Estimated time in minutes (about 1.5 min per km plus about
        5 min per transfer).
    """
    meters = _validate_distance_value(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("Transfer count must be a non-negative integer")
    return (meters / 1000.0) * AVERAGE_MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
