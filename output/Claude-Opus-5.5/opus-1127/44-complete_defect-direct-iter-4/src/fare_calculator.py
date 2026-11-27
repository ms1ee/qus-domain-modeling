"""
Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometers):
    0-6 km   : 3 yuan
    6-12 km  : 4 yuan
    12-22 km : 5 yuan
    22-32 km : 6 yuan
    >32 km   : +1 yuan for every (started) 20 km
"""

import math

# (upper bound in meters inclusive, fare in yuan)
FARE_TIERS = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 6
EXTENDED_STEP = 20000

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MIN = 5.0


class FareCalculationError(Exception):
    """Raised when a fare cannot be computed."""


def Sum_money(distance):
    """Return the fare (yuan, int) for a distance given in meters."""
    if distance is None or isinstance(distance, bool):
        raise FareCalculationError(f"Invalid distance: {distance!r}")
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        raise FareCalculationError(f"Invalid distance: {distance!r}")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise FareCalculationError(f"Invalid distance: {distance!r}")
    for upper, fare in FARE_TIERS:
        if distance <= upper:
            return fare
    extra = math.ceil((distance - EXTENDED_BASE_DISTANCE) / EXTENDED_STEP)
    return EXTENDED_BASE_FARE + int(extra)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance (meters) and transfers."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count is None or transfer_count < 0:
        transfer_count = 0
    riding = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(riding + transfer_count * TRANSFER_TIME_MIN, 1)
