"""
Beijing Subway fare calculation.

Fare tiers (left-closed, right-open intervals):
  [0, 6) km   -> 3 yuan
  [6, 12) km  -> 4 yuan
  [12, 22) km -> 5 yuan
  [22, 32) km -> 6 yuan
  >= 32 km    -> 7 yuan + 1 yuan per additional full 20 km
"""

import math
import numbers

# (upper bound in meters (exclusive), fare in yuan)
FARE_TIERS = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


class FareCalculationError(ValueError):
    """Raised when a fare cannot be computed for the given distance."""


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
        raise FareCalculationError("Distance must be a number, got %r" % (distance,))
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("Distance must be finite")
    if distance < 0:
        raise FareCalculationError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan, int) for a travel distance in meters.

    Fractional meters are rounded up before tier lookup.
    """
    _validate_distance(distance)
    meters = int(math.ceil(distance))
    for upper, fare in FARE_TIERS:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_BASE_DISTANCE) // EXTENDED_STEP


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km + 5 min per transfer."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, numbers.Real) or transfer_count < 0:
        raise FareCalculationError("Transfer count must be a non-negative number")
    return float(distance) / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
