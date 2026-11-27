"""Beijing Subway fare calculation."""

import math

# (upper bound in meters (exclusive), fare in yuan)
FARE_TIERS = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_START = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP = 20000

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MIN = 5.0


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters.

    0-6 km: 3 yuan; 6-12 km: 4; 12-22 km: 5; 22-32 km: 6;
    over 32 km: 7 yuan plus 1 yuan for every further 20 km.
    Boundary values enter the higher tier; fractional meters are rounded up.
    """
    _validate_distance(distance)
    d = int(math.ceil(distance))
    for upper, fare in FARE_TIERS:
        if d < upper:
            return fare
    return EXTENDED_BASE_FARE + (d - EXTENDED_START) // EXTENDED_STEP


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfers."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    travel = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(float(travel + transfer_count * TRANSFER_TIME_MIN), 1)
