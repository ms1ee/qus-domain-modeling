"""Beijing Subway fare calculation.

Fare structure (distance in meters, intervals are left-closed and right-open):
    [0, 6000)            -> 3 yuan
    [6000, 12000)        -> 4 yuan
    [12000, 22000)       -> 5 yuan
    [22000, 32000)       -> 6 yuan
    [32000, 52000)       -> 7 yuan
    then +1 yuan for every additional 20 km (52000-72000 -> 8, ...)
Fractional distances are rounded up to the next whole meter before lookup.
"""

import math
from numbers import Number


# (upper bound in meters, fare in yuan) for the fixed tiers below 32 km.
_FIXED_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
_EXTENDED_BASE_FARE = 7  # fare for [32000, 52000)
_EXTENDED_STEP_M = 20000  # every 20 km
_EXTENDED_STEP_FARE = 1


def _validate_distance(distance):
    """Validate that the distance is a finite, non-negative number."""
    if isinstance(distance, bool) or not isinstance(distance, Number):
        raise TypeError("distance must be a number of meters")
    if isinstance(distance, float) and (math.isnan(distance) or math.isinf(distance)):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a travel distance given in meters.

    Fractional distances are ceiling-rounded to whole meters, and boundary
    values belong to the next higher tier (e.g. 6000 m costs 4 yuan).
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper, fare in _FIXED_TIERS:
        if meters < upper:
            return fare
    return _EXTENDED_BASE_FARE + (meters - 32000) // _EXTENDED_STEP_M * _EXTENDED_STEP_FARE


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: travel distance in meters.
        transfer_count: number of transfers.

    Returns:
        Estimated time in minutes (float).
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    return float(distance) / 1000.0 * 1.5 + transfer_count * 5.0
