"""Fare calculation and travel time estimation for the Beijing Subway.

Fare structure (distances in meters, after ceiling rounding):

* up to 6000 m ............................ 3 yuan (6000 m itself: 3 yuan)
* 6000 m (exclusive) to 12000 m (inclusive) 4 yuan (12000 m: 4 yuan)
* 12000 m (exclusive) to 22000 m (exclusive) 5 yuan
* 22000 m (inclusive) to 32000 m (inclusive) 6 yuan (22000 m and 32000 m: 6 yuan)
* over 32000 m ............................ 7 yuan, +1 yuan for every further
  20000 m (left-closed: 52000 m -> 8 yuan, 72000 m -> 9 yuan, ...)
"""

import math


BASIC_FARE_LIMIT_M = 6000
SECOND_FARE_LIMIT_M = 12000
THIRD_FARE_LIMIT_M = 22000
EXTENDED_START_M = 32000
EXTENDED_STEP_M = 20000

FARE_BASIC = 3
FARE_SECOND = 4
FARE_THIRD = 5
FARE_FOURTH = 6
FARE_EXTENDED_START = 7

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Return the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters (int or float). Fractional
            distances are rounded up before the fare is determined.

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)
    if meters <= BASIC_FARE_LIMIT_M:
        return FARE_BASIC
    if meters <= SECOND_FARE_LIMIT_M:
        return FARE_SECOND
    if meters < THIRD_FARE_LIMIT_M:
        return FARE_THIRD
    if meters <= EXTENDED_START_M:
        return FARE_FOURTH
    return FARE_EXTENDED_START + (meters - EXTENDED_START_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated time in minutes (about 1.5 min per km plus about
        5 min per transfer).
    """
    kilometers = distance / 1000.0
    return kilometers * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
