"""
Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometers):
  0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan,
  beyond 32 km: +1 yuan for every (started) 20 km.
"""

import math

#: (min_km exclusive, max_km inclusive, fare)
FARE_TIERS = [
    (0, 6, 3),
    (6, 12, 4),
    (12, 22, 5),
    (22, 32, 6),
]
EXTENDED_START_KM = 32
EXTENDED_INCREMENT_KM = 20
EXTENDED_INCREMENT_FARE = 1

#: Average train speed in meters per minute (~30 km/h including stops).
AVERAGE_SPEED_M_PER_MIN = 500.0
#: Average time per transfer in minutes.
TRANSFER_TIME_MIN = 5.0


class FareCalculationError(ValueError):
    """Raised when a fare cannot be calculated."""


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError(f"Distance must be a number, got {distance!r}")
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError(f"Invalid distance: {distance!r}")
    if distance < 0:
        raise FareCalculationError("Distance cannot be negative")


def distance_to_km(distance):
    """Convert meters to whole kilometers, rounding up."""
    _validate_distance(distance)
    return int(math.ceil(distance / 1000.0))


def Sum_money(distance):
    """Return the fare in yuan for a distance in meters."""
    km = distance_to_km(distance)
    for _low, high, fare in FARE_TIERS:
        if km <= high:
            return fare
    base = FARE_TIERS[-1][2]
    extra_km = km - EXTENDED_START_KM
    return base + int(math.ceil(extra_km / EXTENDED_INCREMENT_KM)) * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance (meters) and transfers."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        transfer_count = 0
    return round(distance / AVERAGE_SPEED_M_PER_MIN + transfer_count * TRANSFER_TIME_MIN, 1)
