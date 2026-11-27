"""Beijing Subway fare calculation.

Fare structure (distances inclusive of upper bound):
  0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan,
  over 32 km: +1 yuan for every additional 20 km (rounded up).
"""

import math
import numbers

FARE_TIERS = [
    # (max distance in meters inclusive, fare)
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
        raise TypeError("distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must be non-negative")


def Sum_money(distance):
    """Return the fare (yuan) for a travel distance in meters."""
    _validate_distance(distance)
    for max_dist, fare in FARE_TIERS:
        if distance <= max_dist:
            return fare
    extra = distance - EXTENDED_BASE_DISTANCE
    steps = math.ceil(extra / EXTENDED_INCREMENT_DISTANCE)
    return EXTENDED_BASE_FARE + steps * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes (1.5 min/km, 5 min/transfer)."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        transfer_count = 0
    return distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
