"""
Fare calculation module for the Beijing Subway.

Fare structure (distances in meters, fractional meters rounded up):

* 0 - 6 km        : 3 yuan   (boundary 6000 m -> 3 yuan)
* 6 - 12 km       : 4 yuan   (boundary 12000 m -> 4 yuan)
* 12 - 22 km      : 5 yuan
* 22 - 32 km      : 6 yuan   (boundary 22000 m -> 6 yuan, 32000 m -> 6 yuan)
* over 32 km      : 7 yuan for the first 20 km beyond 32 km (32-52 km),
                    then +1 yuan for every additional 20 km (52-72 km: 8 yuan, ...)
"""

import math

BASE_FARE = 3
FARE_TIER_LIMITS = (6000, 12000, 22000, 32000)  # meters
EXTENDED_FARE_START = 7                          # fare just beyond 32 km
EXTENDED_STEP_METERS = 20000                     # +1 yuan per 20 km beyond 32 km

AVG_MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """
    Calculate the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float). Fractional
                  distances are rounded up to the next whole meter.

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is negative or NaN.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance):
        raise ValueError("distance must not be NaN")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)  # ceiling rounding of fractional distances

    if meters <= FARE_TIER_LIMITS[0]:
        return 3
    if meters <= FARE_TIER_LIMITS[1]:
        return 4
    if meters < FARE_TIER_LIMITS[2]:
        return 5
    if meters <= FARE_TIER_LIMITS[3]:
        return 6

    # Extended tier: 7 yuan for (32 km, 52 km], then +1 yuan per 20 km step.
    steps = (meters - FARE_TIER_LIMITS[3] + EXTENDED_STEP_METERS - 1) // EXTENDED_STEP_METERS
    return EXTENDED_FARE_START + steps - 1


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
        raise ValueError("distance must be a non-negative number of meters")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    return (distance / 1000.0) * AVG_MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
