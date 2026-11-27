"""Fare calculation based on the Beijing Subway fare structure.

Tiers (distance in meters, fares in yuan):
    [0, 6000)          3 yuan   (basic tier)
    [6000, 12000)      4 yuan   (progressive tier)
    [12000, 22000)     5 yuan   (progressive tier)
    [22000, 32000)     6 yuan   (progressive tier)
    (32000, ...)       7 yuan, plus 1 yuan for every further 20 km (extended tier)

Boundary values use the PRD-specified fares, which take precedence over the
left-closed tier rule: 6 km -> 3, 12 km -> 4, 22 km -> 6, 32 km -> 6 yuan.
Fractional distances are rounded up to the next whole meter before lookup.
"""

import math

BOUNDARY_FARE_OVERRIDES = {
    6000: 3,
    12000: 4,
    22000: 6,
    32000: 6,
}

EXTENDED_TIER_START_M = 32000
EXTENDED_STEP_M = 20000
EXTENDED_BASE_FARE = 7

# Average travel speed based estimate: minutes per kilometer and per transfer.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Return the subway fare in yuan for a travel distance.

    Args:
        distance: Travel distance in meters (fractions are rounded up).

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative or not finite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)
    if meters in BOUNDARY_FARE_OVERRIDES:
        return BOUNDARY_FARE_OVERRIDES[meters]
    if meters < 6000:
        return 3
    if meters < 12000:
        return 4
    if meters < 22000:
        return 5
    if meters < EXTENDED_TIER_START_M:
        return 6
    # Extended tier: 7 yuan for (32 km, 52 km), 8 yuan for [52 km, 72 km), ...
    return EXTENDED_BASE_FARE + (meters - EXTENDED_TIER_START_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated time in minutes (about 1.5 min/km plus 5 min per transfer).
    """
    if distance < 0:
        raise ValueError("distance must not be negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
