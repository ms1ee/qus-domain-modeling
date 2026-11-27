"""Fare and travel-time calculation for Beijing Subway trips.

Fare tiers (distance in meters):
    up to 6 km              -> 3 yuan
    up to 12 km             -> 4 yuan
    under 22 km             -> 5 yuan
    up to 32 km             -> 6 yuan
    over 32 km              -> 6 yuan + 1 yuan per additional 20 km (rounded up)

Boundary values follow the explicit examples given in the PRD:
6000 m -> 3 yuan, 12000 m -> 4 yuan, 22000 m -> 6 yuan, 32000 m -> 6 yuan.
Fractional distances above 32 km are rounded up to the next 20 km step.
"""

import math

BASE_FARE_YUAN = 3
EXTENDED_STEP_METERS = 20000
EXTENDED_STEP_FARE_YUAN = 1

# Estimated-time model parameters.
MINUTES_PER_KILOMETER = 1.5
MINUTES_PER_TRANSFER = 5.0


def _validate_distance(distance):
    """Ensure a distance value is a finite, non-negative number."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    return float(distance)


def Sum_money(distance):
    """Calculate the subway fare for a trip distance.

    Args:
        distance: Trip distance in meters (int or float).

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not numeric.
        ValueError: If distance is negative, NaN, or infinite.
    """
    d = _validate_distance(distance)
    if d <= 6000:
        return 3
    if d <= 12000:
        return 4
    if d < 22000:
        return 5
    if d <= 32000:
        return 6
    # Extended tier: +1 yuan per 20 km beyond 32 km, fractions rounded up.
    steps = math.ceil((d - 32000) / EXTENDED_STEP_METERS)
    return 6 + steps * EXTENDED_STEP_FARE_YUAN


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Trip distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated time in minutes (about 1.5 min/km plus 5 min per transfer).
    """
    d = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (d / 1000.0) * MINUTES_PER_KILOMETER + transfer_count * MINUTES_PER_TRANSFER
