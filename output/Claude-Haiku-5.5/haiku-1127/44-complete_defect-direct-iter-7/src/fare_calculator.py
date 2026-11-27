"""Beijing Subway fare calculation and travel time estimation.

Fare structure (distance is rounded up to whole kilometers):
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    beyond 32 km: +1 yuan for every additional 20 km (or part thereof)
"""

import math

BASE_FARE_YUAN = 3
# (upper bound in kilometers, inclusive; fare in yuan)
FARE_TIERS = ((6, 3), (12, 4), (22, 5), (32, 6))
EXTENSION_THRESHOLD_KM = 32
EXTENSION_STEP_KM = 20
EXTENSION_STEP_FARE = 1

# Average operating speed used for time estimation (km/h).
AVERAGE_SPEED_KMH = 35.0
# Average extra time spent per transfer (minutes).
TRANSFER_TIME_MIN = 5.0


def _validate_distance(distance):
    """Validate a distance in meters and return it as a float."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    return float(distance)


def Sum_money(distance):
    """Return the subway fare (integer yuan) for a trip of ``distance`` meters.

    Fractional kilometers are rounded up (ceiling), so 6.2 km is charged as 7 km.
    A distance of 0 meters costs nothing.
    """
    distance = _validate_distance(distance)
    if distance == 0:
        return 0

    km = math.ceil(distance / 1000.0)
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    extra_km = km - EXTENSION_THRESHOLD_KM
    steps = math.ceil(extra_km / EXTENSION_STEP_KM)
    return FARE_TIERS[-1][1] + steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance, transfer_count):
    """Return the estimated travel time in minutes.

    Travel time is derived from the distance at AVERAGE_SPEED_KMH, plus
    TRANSFER_TIME_MIN for every transfer.
    """
    distance = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return float(travel_minutes + transfer_count * TRANSFER_TIME_MIN)
