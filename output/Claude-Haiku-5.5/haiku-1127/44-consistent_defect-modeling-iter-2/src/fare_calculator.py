"""Fare calculation and travel-time estimation for Beijing Subway trips.

Fare tiers (distance in meters):
    0 - 6 km           3 yuan
    6 - 12 km          4 yuan
    12 - 22 km         5 yuan
    22 - 32 km         6 yuan
    over 32 km         7 yuan for 32-52 km, then +1 yuan for every further
                       20 km (52-72 km: 8 yuan, and so on)

Boundary values follow the examples in the PRD (6000 m -> 3 yuan, 12000 m ->
4 yuan, 22000 m -> 6 yuan, 32000 m -> 6 yuan). Fractional distances are rounded
up to the next whole meter before lookup.
"""

import math

BASE_FARE_YUAN = 3
EXTENDED_STEP_METERS = 20000
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Distance in meters (fractional values are rounded up).

    Returns:
        The fare in whole yuan.

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is negative or NaN.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or distance < 0:
        raise ValueError("distance must be a non-negative number")
    meters = math.ceil(distance)

    if meters <= 6000:
        return 3
    if meters <= 12000:
        return 4
    if meters < 22000:
        return 5
    if meters <= 32000:
        return 6
    # Extended tier: 7 yuan for (32000, 52000], 8 yuan for (52000, 72000], ...
    steps = math.ceil((meters - 32000) / EXTENDED_STEP_METERS)
    return 6 + steps


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: Distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated time in minutes (about 1.5 min per km plus 5 min per transfer).
    """
    if distance < 0 or transfer_count < 0:
        raise ValueError("distance and transfer count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
