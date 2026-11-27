"""Fare calculation and travel-time estimation for Beijing Subway trips.

Fare structure (distances in meters, intervals are left-closed, right-open):
    [0, 6000)            -> 3 yuan
    [6000, 12000)        -> 4 yuan
    [12000, 22000)       -> 5 yuan
    [22000, 32000]       -> 6 yuan   (32000 m itself is charged 6 yuan)
    (32000, 52000)       -> 7 yuan   (extended tier: +1 yuan every 20 km)
    [52000, 72000)       -> 8 yuan
    ...
Fractional distances are rounded up (ceiling) to the next whole meter.
"""

import bisect
import math

# Start (inclusive) of each basic/progressive tier, in meters.
BASE_TIER_STARTS = (0, 6000, 12000, 22000)
# Fare for each basic/progressive tier, in yuan (same order as BASE_TIER_STARTS).
BASE_TIER_FARES = (3, 4, 5, 6)
# Largest distance handled by the basic/progressive table (32 km, inclusive).
BASE_TIER_UPPER_M = 32000
# Length of each extended-tier step, in meters (20 km).
EXTENDED_STEP_M = 20000
# Fare of the extended tier's base (applies to the last basic tier).
EXTENDED_BASE_FARE = 6

# Travel-time estimation constants.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Travelled distance in meters. Fractional values are rounded up.

    Returns:
        Fare in yuan (int).

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    meters = math.ceil(distance)  # ceiling rounding for fractional distances
    if meters <= BASE_TIER_UPPER_M:
        index = bisect.bisect_right(BASE_TIER_STARTS, meters) - 1
        return BASE_TIER_FARES[index]

    # Extended tier: one extra yuan for every full 20 km beyond 32 km.
    steps = (meters - BASE_TIER_UPPER_M) // EXTENDED_STEP_M
    return EXTENDED_BASE_FARE + steps + 1


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated time in minutes (about 1.5 min per km plus 5 min per transfer).
    """
    return float((distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
