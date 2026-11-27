"""Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometers):
  up to 6 km: 3 yuan; up to 12 km: 4 yuan; up to 22 km: 5 yuan;
  up to 32 km: 6 yuan; beyond 32 km: +1 yuan per (started) 20 km.
"""

import math

# (upper bound in km inclusive, fare)
FARE_TABLE = [(6, 3), (12, 4), (22, 5), (32, 6)]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_STEP_KM = 20

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number")
    if distance != distance or distance in (float("inf"), float("-inf")):
        raise ValueError("Distance must be finite")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    _validate_distance(distance)
    km = math.ceil(distance / 1000.0)
    for upper, fare in FARE_TABLE:
        if km <= upper:
            return fare
    extra = km - EXTENDED_BASE_KM
    return EXTENDED_BASE_FARE + int(math.ceil(extra / float(EXTENDED_STEP_KM)))


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km plus 5 min per transfer."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
