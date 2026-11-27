"""
Beijing Subway fare calculation.

Fare structure (distance in meters, lower bound inclusive):

* [0, 6000)       -> 3 yuan  (basic tier)
* [6000, 12000)   -> 4 yuan
* [12000, 22000)  -> 5 yuan
* [22000, 32000)  -> 6 yuan
* [32000, ...)    -> 7 yuan + 1 yuan for every further 20 km (extended tier)

Fractional distances are rounded up to the next whole meter.
"""

import math

#: (upper bound exclusive in meters, fare in yuan, tier name)
FARE_TIERS = [
    (6000, 3, "Basic Tier (0-6 km)"),
    (12000, 4, "Progressive Tier (6-12 km)"),
    (22000, 5, "Progressive Tier (12-22 km)"),
    (32000, 6, "Progressive Tier (22-32 km)"),
]
EXTENDED_START_DISTANCE = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000

#: Average operating speed (km/h) used for time estimation.
AVERAGE_SPEED_KMH = 35.0
#: Minutes added per transfer.
TRANSFER_TIME_MINUTES = 5.0
#: Minutes for entering/leaving the stations.
BASE_TIME_MINUTES = 2.0


class FareCalculationError(ValueError):
    """Raised for invalid fare calculation input."""


def _normalize_distance(distance):
    if isinstance(distance, bool):
        raise FareCalculationError("Distance must be a number")
    if not isinstance(distance, (int, float)):
        try:
            distance = float(distance)
        except (TypeError, ValueError):
            raise FareCalculationError(f"Distance must be a number: {distance!r}")
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError(f"Distance must be finite: {distance!r}")
    if distance < 0:
        raise FareCalculationError(f"Distance cannot be negative: {distance!r}")
    return int(math.ceil(distance))


def Sum_money(distance):
    """Return the fare (yuan, int) for a trip of ``distance`` meters."""
    d = _normalize_distance(distance)
    for upper, fare, _ in FARE_TIERS:
        if d < upper:
            return fare
    return EXTENDED_BASE_FARE + (d - EXTENDED_START_DISTANCE) // EXTENDED_INCREMENT_DISTANCE


def get_fare_tier(distance):
    """Return the human-readable tier name for ``distance`` meters."""
    d = _normalize_distance(distance)
    for upper, _, name in FARE_TIERS:
        if d < upper:
            return name
    return "Extended Tier (over 32 km)"


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfers."""
    d = _normalize_distance(distance)
    if transfer_count is None:
        transfer_count = 0
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)):
        raise ValueError("transfer_count must be a number")
    if transfer_count < 0:
        raise ValueError("transfer_count cannot be negative")
    if d == 0:
        return 0.0
    ride = d / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    total = ride + transfer_count * TRANSFER_TIME_MINUTES + BASE_TIME_MINUTES
    return round(total, 1)
