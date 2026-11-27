"""
Fare calculation for the Beijing Subway.

Fare structure (distance in meters, boundary values fall into the higher tier,
ceiling rounding is applied to fractional meters first):

    distance <= 6 km         -> 3 yuan   (basic tier)
    6 km  < distance <= 12 km -> 4 yuan   (progressive tier)
    12 km < distance < 22 km  -> 5 yuan
    22 km <= distance <= 32 km -> 6 yuan
    distance > 32 km         -> 7 yuan, +1 yuan for every further 20 km
                                (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Boundary examples: 6000 m -> 3, 12000 m -> 4, 22000 m -> 6, 32000 m -> 6.
"""

import math


BASIC_FARE_YUAN = 3
PROGRESSIVE_FARE_YUAN = 4
MID_FARE_YUAN = 5
UPPER_FARE_YUAN = 6
EXTENDED_BASE_FARE_YUAN = 7

BASIC_LIMIT_M = 6000
PROGRESSIVE_LIMIT_M = 12000
MID_LIMIT_M = 22000
UPPER_LIMIT_M = 32000
EXTENDED_STEP_M = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Calculate the fare for a journey.

    Args:
        distance: Travel distance in meters (int or float). Fractional meters
                  are rounded up (ceiling rounding).

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is missing, NaN, infinite or negative.
    """
    if distance is None:
        raise ValueError("Distance is required to calculate a fare")
    value = float(distance)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Distance must be a finite number")
    if value < 0:
        raise ValueError("Distance cannot be negative")

    meters = math.ceil(value)
    if meters <= BASIC_LIMIT_M:
        return BASIC_FARE_YUAN
    if meters <= PROGRESSIVE_LIMIT_M:
        return PROGRESSIVE_FARE_YUAN
    if meters < MID_LIMIT_M:
        return MID_FARE_YUAN
    if meters <= UPPER_LIMIT_M:
        return UPPER_FARE_YUAN
    # Extended tier: 7 yuan for (32 km, 52 km), +1 yuan per further 20 km.
    return EXTENDED_BASE_FARE_YUAN + (meters - UPPER_LIMIT_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated time in minutes.

    Raises:
        ValueError: If distance or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
