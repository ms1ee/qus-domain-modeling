"""Beijing Subway fare calculation.

Tiers are left-closed / right-open intervals in meters:
  [0, 6000) -> 3, [6000, 12000) -> 4, [12000, 22000) -> 5,
  [22000, 32000) -> 6, then +1 yuan per started 20 km above 32 km
  ([32000, 52000) -> 7, [52000, 72000) -> 8, ...).
Fractional distances are rounded up to the next whole meter.
"""

import math

# (upper bound in meters exclusive, fare in yuan)
FARE_STRUCTURE = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_START = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


class FareCalculationError(ValueError):
    """Raised when a fare cannot be computed for the given distance."""


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError("Distance must be a number, got %r" % (distance,))
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("Distance must be finite")
    if distance < 0:
        raise FareCalculationError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a travel distance given in meters."""
    _validate_distance(distance)
    meters = int(math.ceil(distance))
    for upper, fare in FARE_STRUCTURE:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START) // EXTENDED_STEP


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes (1.5 min/km + 5 min/transfer)."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
