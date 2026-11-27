"""
Beijing Subway fare calculation.

Official structure:
  * up to 6 km (inclusive): 3 yuan
  * 6-12 km: 4 yuan
  * 12-22 km: 5 yuan
  * 22-32 km: 6 yuan
  * above 32 km: +1 yuan for every additional 20 km (or part thereof)
Fractional distances are rounded up into the next tier.
"""

import math

# (upper bound in km inclusive, fare in yuan)
FARE_TIERS = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_KM = 20

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must not be negative")


def Sum_money(distance):
    """Return the fare in yuan for a distance given in meters."""
    _validate_distance(distance)
    km = distance / 1000.0
    for upper, fare in FARE_TIERS:
        if km <= upper:
            return fare
    extra = math.ceil((km - EXTENDED_BASE_KM) / EXTENDED_INCREMENT_KM)
    return EXTENDED_BASE_FARE + max(1, extra)


def calculate_fare(distance):
    """Alias of Sum_money."""
    return Sum_money(distance)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes (1.5 min/km + 5 min/transfer)."""
    _validate_distance(distance)
    if transfer_count is None:
        transfer_count = 0
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
