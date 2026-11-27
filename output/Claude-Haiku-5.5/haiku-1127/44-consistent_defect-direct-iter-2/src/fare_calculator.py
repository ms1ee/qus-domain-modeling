"""Fare and travel time calculation for the Beijing Subway."""

import math

# Base fare tiers as (upper bound in meters, fare in yuan).
# Boundary values follow the PRD examples: 6 km -> 3 yuan, 12 km -> 4 yuan,
# 22 km -> 6 yuan, 32 km -> 6 yuan.
EXTENDED_THRESHOLD_M = 32000   # distances above this use the extended tier
EXTENDED_BASE_FARE = 7         # fare for (32 km, 52 km]
EXTENDED_STEP_M = 20000        # +1 yuan per additional 20 km

ESTIMATED_MINUTES_PER_KM = 1.5
ESTIMATED_MINUTES_PER_TRANSFER = 5.0


def _base_fare(meters):
    """Return the base-tier fare for a distance that is at most 32 km.

    Intervals (PRD boundary rules):
        0 - 6 km (inclusive)     -> 3 yuan
        6 - 12 km (inclusive)    -> 4 yuan
        12 - 22 km (exclusive)   -> 5 yuan
        22 - 32 km (inclusive)   -> 6 yuan
    """
    if meters <= 6000:
        return 3
    if meters <= 12000:
        return 4
    if meters < 22000:
        return 5
    return 6


def Sum_money(distance):
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: distance in meters (int or float). Fractional meters are
            rounded up before the fare is determined.

    Returns:
        The fare in yuan as an int.

    Raises:
        TypeError: if distance is not a number.
        ValueError: if distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    meters = math.ceil(distance)
    if meters > EXTENDED_THRESHOLD_M:
        extra = meters - EXTENDED_THRESHOLD_M
        return EXTENDED_BASE_FARE + (extra - 1) // EXTENDED_STEP_M
    return _base_fare(meters)


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: distance in meters.
        transfer_count: number of transfers.

    Returns:
        Estimated time in minutes (about 1.5 min per km plus 5 min per transfer).
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if distance < 0 or transfer_count < 0:
        raise ValueError("distance and transfer_count must be non-negative")
    return (distance / 1000.0) * ESTIMATED_MINUTES_PER_KM + \
        transfer_count * ESTIMATED_MINUTES_PER_TRANSFER
