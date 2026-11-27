"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distance in kilometers, rounded up):
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    > 32 km   : 6 yuan plus 1 yuan for every further (or partial) 20 km
"""

import math

# (upper bound in km inclusive, fare in yuan)
BASE_FARE_TABLE = ((6, 3), (12, 4), (22, 5), (32, 6))
EXTENSION_STEP_KM = 20
EXTENSION_STEP_FARE = 1

AVERAGE_SPEED_KMH = 35.0    # average operating speed of the subway
BOARDING_TIME_MIN = 3.0     # fixed time for entering and boarding
TRANSFER_TIME_MIN = 5.0     # walking and waiting time per transfer


def _check_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must not be negative")


def Sum_money(distance):
    """Return the fare in yuan for a journey of ``distance`` meters.

    Fractional kilometers are rounded up (ceiling), so any part of a
    kilometer is charged as a full kilometer for tier selection.
    """
    _check_distance(distance)
    km = math.ceil(distance / 1000)  # integer kilometers, rounded up
    for upper_km, fare in BASE_FARE_TABLE:
        if km <= upper_km:
            return fare
    last_upper, last_fare = BASE_FARE_TABLE[-1]
    extra_km = km - last_upper
    extra_steps = (extra_km + EXTENSION_STEP_KM - 1) // EXTENSION_STEP_KM
    return last_fare + extra_steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: total distance in meters.
        transfer_count: number of line transfers.

    Returns:
        Estimated time in minutes (float, one decimal place).
    """
    _check_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    riding_min = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_TIME_MIN + riding_min + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
