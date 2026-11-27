"""
Beijing Subway fare calculation.

Fare tiers (left-closed, right-open intervals, distances in kilometers):

* [0, 6)   -> 3 yuan
* [6, 12)  -> 4 yuan
* [12, 22) -> 5 yuan
* [22, 32) -> 6 yuan
* >= 32    -> 7 yuan + 1 yuan for every additional full 20 km
"""

import math

# (min meters inclusive, max meters exclusive, fare, tier name)
FARE_TIERS = [
    (0, 6000, 3, "Basic Tier (0-6 km)"),
    (6000, 12000, 4, "Progressive Tier (6-12 km)"),
    (12000, 22000, 5, "Progressive Tier (12-22 km)"),
    (22000, 32000, 6, "Progressive Tier (22-32 km)"),
]
EXTENDED_START_DISTANCE = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance in meters.

    Fractional meters are rounded up before tier lookup.
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for low, high, fare, _name in FARE_TIERS:
        if low <= meters < high:
            return fare
    extra = (meters - EXTENDED_START_DISTANCE) // EXTENDED_INCREMENT_DISTANCE
    return EXTENDED_BASE_FARE + extra * EXTENDED_INCREMENT_FARE


def get_fare_tier_name(distance):
    """Return a descriptive name of the fare tier for the distance (meters)."""
    _validate_distance(distance)
    meters = math.ceil(distance)
    for low, high, _fare, name in FARE_TIERS:
        if low <= meters < high:
            return name
    return "Extended Tier (over 32 km)"


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km plus 5 min per transfer."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)):
        raise TypeError("Transfer count must be a number")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
