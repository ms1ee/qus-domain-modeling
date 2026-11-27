"""Fare calculation according to the Beijing Subway fare structure.

* 0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan
* over 32 km: 7 yuan, plus 1 yuan for every further 20 km
Boundary values belong to the higher tier (e.g. exactly 6 km costs 4 yuan).
Fractional distances are rounded up to whole meters.
"""

import math

# (min distance inclusive, max distance exclusive, fare, tier type), meters
FARE_TIERS = [
    (0, 6000, 3, "basic"),
    (6000, 12000, 4, "progressive"),
    (12000, 22000, 5, "progressive"),
    (22000, 32000, 6, "progressive"),
]
EXTENDED_START_DISTANCE = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000

# Parameters of the travel time estimate.
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a number" % name)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % name)
    if value < 0:
        raise ValueError("%s must be non-negative" % name)


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    _validate_number(distance, "distance")
    d = math.ceil(distance)
    for low, high, fare, _tier in FARE_TIERS:
        if low <= d < high:
            return fare
    return EXTENDED_BASE_FARE + (d - EXTENDED_START_DISTANCE) // EXTENDED_INCREMENT_DISTANCE


def get_fare_tier(distance):
    """Return the tier type name ("basic", "progressive", "extended")."""
    _validate_number(distance, "distance")
    d = math.ceil(distance)
    for low, high, _fare, tier in FARE_TIERS:
        if low <= d < high:
            return tier
    return "extended"


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfers."""
    _validate_number(distance, "distance")
    _validate_number(transfer_count, "transfer_count")
    riding = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(riding + transfer_count * TRANSFER_TIME_MINUTES, 1)


def format_fare(fare):
    return "Fare: %d yuan" % fare
