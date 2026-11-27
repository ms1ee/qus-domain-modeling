"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distances in meters, fractional meters are rounded up):
    0 - 6 km      : 3 yuan
    6 - 12 km     : 4 yuan
    12 - 22 km    : 5 yuan
    22 - 32 km    : 6 yuan
    over 32 km    : 7 yuan, plus 1 yuan for every further 20 km
"""

import math

# (lower bound in meters inclusive, upper bound in meters exclusive, fare in yuan)
FARE_TIERS = (
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
)
EXTENDED_START_M = 32000
EXTENDED_STEP_M = 20000
EXTENDED_BASE_FARE = 7

AVERAGE_SPEED_KMH = 35.0     # average in-service speed including station dwell
BOARDING_TIME_MIN = 1.0      # time to enter the system and board
TRANSFER_TIME_MIN = 4.0      # walking and waiting time per transfer


def _validate_distance(distance):
    """Validate a distance value in meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance in meters.

    Boundary behaviour: exactly 6000 m costs 4 yuan, 12000 m costs 5 yuan,
    22000 m costs 6 yuan and 32000 m costs 7 yuan.

    Args:
        distance: Travelled distance in meters (fractions are rounded up).

    Returns:
        Fare as an integer number of yuan.
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for _lower, upper, fare in FARE_TIERS:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line transfers on the trip.

    Returns:
        Estimated travel time in minutes, rounded to two decimals.
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    speed_m_per_min = AVERAGE_SPEED_KMH * 1000.0 / 60.0
    minutes = (
        distance / speed_m_per_min
        + transfer_count * TRANSFER_TIME_MIN
        + BOARDING_TIME_MIN
    )
    return round(minutes, 2)
