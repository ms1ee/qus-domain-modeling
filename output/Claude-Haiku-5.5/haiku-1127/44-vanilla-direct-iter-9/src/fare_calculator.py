"""Fare calculation based on the Beijing Subway fare structure.

Fare tiers (distance intervals are left-closed, right-open):
    [0, 6) km      -> 3 yuan
    [6, 12) km     -> 4 yuan
    [12, 22) km    -> 5 yuan
    [22, 32) km    -> 6 yuan
    [32, 52) km    -> 7 yuan
    [52, 72) km    -> 8 yuan   (+1 yuan per additional 20 km)

Fractional meters are rounded up (ceiling) before tier lookup.
"""

import math
from typing import List, Tuple

# (upper bound in meters, fare for distances below that bound)
TIER_TABLE: List[Tuple[int, int]] = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_START_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_METERS = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _validate_distance(distance) -> None:
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a travel distance in meters.

    Args:
        distance: Travelled distance in meters (fractions are rounded up).

    Returns:
        The fare in yuan as an integer.

    Raises:
        TypeError: If the distance is not a number.
        ValueError: If the distance is negative, NaN or infinite.
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper_bound, fare in TIER_TABLE:
        if meters < upper_bound:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated time in minutes (about 1.5 min/km plus 5 min per transfer).
    """
    _validate_distance(distance)
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
