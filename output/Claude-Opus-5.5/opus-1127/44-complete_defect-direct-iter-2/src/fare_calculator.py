"""Beijing Subway fare calculation."""

import math

# (upper bound in km inclusive, fare in yuan)
FARE_TIERS = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_STEP_KM = 20
EXTENDED_BASE_FARE = 6

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MIN = 5.0


def _check_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must be non-negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance in meters.

    Fractional kilometres are rounded up before tier lookup:
    0-6 km 3 yuan, 6-12 km 4, 12-22 km 5, 22-32 km 6, then +1 yuan per
    started 20 km beyond 32 km.
    """
    _check_distance(distance)
    km = math.ceil(distance / 1000.0)
    for upper, fare in FARE_TIERS:
        if km <= upper:
            return fare
    return EXTENDED_BASE_FARE + math.ceil((km - EXTENDED_BASE_KM) / EXTENDED_STEP_KM)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance (meters) and transfers."""
    _check_distance(distance)
    if transfer_count is None or transfer_count < 0:
        transfer_count = 0
    minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0 + transfer_count * TRANSFER_TIME_MIN
    return round(float(minutes), 1)
