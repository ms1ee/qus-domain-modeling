"""Fare and travel time calculation for the Beijing Subway.

Fare structure (distances in meters):
    [0, 6000)          -> 3 yuan
    [6000, 12000)      -> 4 yuan
    [12000, 22000)     -> 5 yuan
    [22000, 32000)     -> 6 yuan
    [32000, ...)       -> 7 yuan, plus 1 yuan for every further 20 km
Intervals are left-closed, right-open, so boundary values enter the higher tier.
Fractional distances are rounded up (ceiling) before the tier lookup.
"""

import math

# (lower bound inclusive, upper bound exclusive, fare in yuan) in meters.
BASE_FARE_TIERS = (
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
)

EXTENDED_START_M = 32000      # start of the extended tier
EXTENDED_STEP_M = 20000       # every 20 km beyond the start...
EXTENDED_BASE_FARE = 7        # ...adds 1 yuan, starting from 7 yuan

MINUTES_PER_KM = 1.5          # average travel time per kilometer
MINUTES_PER_TRANSFER = 5.0    # average time spent per transfer


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a travelled distance in meters.

    Args:
        distance: travelled distance in meters (int or float, non-negative).

    Returns:
        The fare as an integer number of yuan.

    Raises:
        ValueError: if the distance is not a finite non-negative number.
    """
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Distance must be a number, got {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Distance must be a finite number")
    if value < 0:
        raise ValueError("Distance cannot be negative")

    # Round fractional distances up so that any partial meter is charged.
    meters = math.ceil(value)

    for lower, upper, fare in BASE_FARE_TIERS:
        if lower <= meters < upper:
            return fare

    # Extended tier: 7 yuan from 32 km, plus 1 yuan for each full 20 km.
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate the travel time in minutes.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line transfers on the route.

    Returns:
        Estimated travel time in minutes (about 1.5 min per km plus 5 min per transfer).

    Raises:
        ValueError: if the distance or transfer count is negative.
    """
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    kilometers = distance / 1000.0
    return kilometers * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
