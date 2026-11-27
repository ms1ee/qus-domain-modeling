"""Beijing Subway fare calculation.

Fare structure (distance in kilometers):
    [0, 6)   -> 3 yuan
    [6, 12)  -> 4 yuan
    [12, 22) -> 5 yuan
    [22, 32) -> 6 yuan
    >= 32    -> 7 yuan, +1 yuan for every further 20 km
Fractional distances (meters) are rounded up before the lookup.
"""

import math

# (exclusive upper bound in meters, fare in yuan)
FARE_TABLE = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_START_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_METERS = 20000

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan, int) for a travel distance given in meters."""
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper, fare in FARE_TABLE:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS


def calculate_fare(distance):
    """Alias of :func:`Sum_money`."""
    return Sum_money(distance)


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfers."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)):
        raise TypeError("Transfer count must be a number")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    riding = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    total = riding + transfer_count * TRANSFER_TIME_MINUTES
    return round(float(total), 1)
