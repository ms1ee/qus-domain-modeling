"""
Beijing Subway fare calculation.

Tiers (left-closed, right-open, in meters):
  [0, 6000)      -> 3 yuan
  [6000, 12000)  -> 4 yuan
  [12000, 22000) -> 5 yuan
  [22000, 32000) -> 6 yuan
  >= 32000       -> 7 yuan + 1 yuan per additional full 20 km
Fractional distances are rounded up to the next whole meter.
"""

import math

#: (min meters inclusive, max meters exclusive, fare yuan)
FARE_TIERS = [
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
]
EXTENDED_START = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    _validate_distance(distance)
    meters = math.ceil(distance)
    for low, high, fare in FARE_TIERS:
        if low <= meters < high:
            return fare
    extra = (meters - EXTENDED_START) // EXTENDED_INCREMENT_DISTANCE
    return EXTENDED_BASE_FARE + extra * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes (1.5 min/km, 5 min per transfer)."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        transfer_count = 0
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
