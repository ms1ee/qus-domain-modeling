"""Fare and travel time calculation for the Beijing Subway.

Fare structure:
    0 - 6 km        : 3 yuan   (distance < 6000 m)
    6 - 12 km       : 4 yuan   (6000 m <= distance < 12000 m)
    12 - 22 km      : 5 yuan   (12000 m <= distance < 22000 m)
    22 - 32 km      : 6 yuan   (22000 m <= distance < 32000 m)
    over 32 km      : 7 yuan, plus 1 yuan for every further 20 km

Fractional meters are rounded up before tier lookup.
"""

import math

# (upper bound in meters exclusive, fare in yuan) for the basic/progressive tiers.
BASIC_FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
EXTENDED_BASE_DISTANCE_M = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_M = 20000

AVERAGE_SPEED_KMH = 35.0
BOARDING_TIME_MIN = 2.0
TRANSFER_TIME_MIN = 5.0


def _validate_distance(distance):
    """Validate a non-negative, finite numeric distance in meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance) -> int:
    """Calculate the subway fare in yuan for a travel distance.

    Args:
        distance: Travel distance in meters (fractional values are rounded up).

    Returns:
        The fare in yuan as an integer.

    Raises:
        TypeError: If distance is not numeric.
        ValueError: If distance is negative, NaN or infinite.
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper_bound, fare in BASIC_FARE_TIERS:
        if meters < upper_bound:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_BASE_DISTANCE_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate the travel time in minutes.

    The estimate combines a fixed boarding allowance, travel time at an
    average operating speed, and a fixed walking allowance per transfer.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of line transfers.

    Returns:
        Estimated travel time in minutes, rounded to one decimal place.
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_TIME_MIN + travel_minutes + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
