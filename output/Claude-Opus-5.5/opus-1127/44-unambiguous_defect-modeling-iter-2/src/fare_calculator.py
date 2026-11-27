"""Beijing Subway fare calculation.

Fare structure (distance in meters, boundaries belong to the higher tier):

* [0, 6000)       -> 3 yuan
* [6000, 12000)   -> 4 yuan
* [12000, 22000)  -> 5 yuan
* [22000, 32000)  -> 6 yuan
* >= 32000        -> 7 yuan plus 1 yuan for every further 20 km
"""

import math

# (min distance inclusive, max distance exclusive, fare)
FARE_TIERS = [
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
]
EXTENDED_START = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000

AVERAGE_SPEED_KMH = 35.0     # average operating speed including stops
TRANSFER_TIME_MINUTES = 5.0  # average time per transfer


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number, got %r" % (distance,))
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare in yuan for a distance given in meters.

    Fractional distances are rounded up to the next whole meter.
    """
    _validate_distance(distance)
    d = math.ceil(distance)
    for low, high, fare in FARE_TIERS:
        if low <= d < high:
            return fare
    return EXTENDED_BASE_FARE + (d - EXTENDED_START) // EXTENDED_INCREMENT_DISTANCE


def get_fare_tier_name(distance):
    """Human readable name of the tier for a distance in meters."""
    _validate_distance(distance)
    d = math.ceil(distance)
    if d < 6000:
        return "Basic Tier"
    if d < EXTENDED_START:
        return "Progressive Tier"
    return "Extended Tier"


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance in meters."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)) or transfer_count < 0:
        raise ValueError("Transfer count must be a non-negative number")
    minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0 + transfer_count * TRANSFER_TIME_MINUTES
    return round(float(minutes), 2)
