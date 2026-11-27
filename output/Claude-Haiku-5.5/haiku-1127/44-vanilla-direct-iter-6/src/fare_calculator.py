"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distances in meters, left-closed / right-open intervals):
    [0, 6000)          -> 3 yuan
    [6000, 12000)      -> 4 yuan
    [12000, 22000)     -> 5 yuan
    [22000, 32000)     -> 6 yuan
    [32000, ...)       -> 7 yuan, plus 1 yuan for every further 20 km
                          (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)
Fractional distances are rounded up to the next whole meter before the tier
lookup, so a boundary value belongs to the next higher tier.
"""

import math

# (exclusive upper bound in meters, fare in yuan) for the base and progressive tiers.
FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)

EXTENSION_START_M = 32000      # start of the extended tier
EXTENSION_STEP_M = 20000       # every 20 km beyond the extension start...
EXTENSION_STEP_FARE = 1        # ...adds 1 yuan
EXTENSION_BASE_FARE = 7        # fare for the first extended segment (32-52 km)

# Travel time model
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Compute the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float). Fractional
            values are rounded up to the next whole meter.

    Returns:
        int: The fare in yuan.

    Raises:
        TypeError: If ``distance`` is not a real number.
        ValueError: If ``distance`` is negative or NaN.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance):
        raise ValueError("distance must not be NaN")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    meters = math.ceil(distance)
    for upper_bound, fare in FARE_TIERS:
        if meters < upper_bound:
            return fare
    extra_steps = (meters - EXTENSION_START_M) // EXTENSION_STEP_M
    return EXTENSION_BASE_FARE + extra_steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line transfers.

    Returns:
        float: Estimated travel time in minutes (about 1.5 min per km plus
        about 5 min per transfer).

    Raises:
        ValueError: If the distance or transfer count is negative.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    kilometers = distance / 1000.0
    return kilometers * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
