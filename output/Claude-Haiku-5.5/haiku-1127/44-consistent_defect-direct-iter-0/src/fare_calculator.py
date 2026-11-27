"""Fare calculation for the Beijing Subway fare structure.

Fare tiers (left-closed, right-open intervals, distances in meters):
    [0, 6000)          -> 3 yuan
    [6000, 12000)      -> 4 yuan
    [12000, 22000)     -> 5 yuan
    [22000, 32000)     -> 6 yuan
    [32000, ...)       -> 6 yuan plus 1 yuan for every additional 20 km
                          (or part thereof), e.g. 32-52 km: 7 yuan,
                          52-72 km: 8 yuan.

Fractional meters are rounded up (ceiling) before the tier lookup.
"""

import math

# (exclusive upper bound in meters, fare in yuan) for the base tiers.
BASE_FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
EXTENDED_START_M = 32000
EXTENDED_STEP_M = 20000
EXTENDED_BASE_FARE = 6

# Walking/riding estimates used by calculate_estimated_time.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: Travel distance in meters (int or float). Fractional meters
            are rounded up.

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If distance is negative or not a number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("distance must be a number of meters")
    if distance < 0 or math.isnan(distance):
        raise ValueError("distance must be non-negative")

    meters = math.ceil(distance)
    for upper_bound, fare in BASE_FARE_TIERS:
        if meters < upper_bound:
            return fare

    # Extended tier: distance at or beyond 32 km.
    extra = meters - EXTENDED_START_M
    steps = -(-extra // EXTENDED_STEP_M)  # ceiling division
    return EXTENDED_BASE_FARE + steps


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time of a route in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        float: Estimated time in minutes (about 1.5 min per km plus about
        5 min per transfer).
    """
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
