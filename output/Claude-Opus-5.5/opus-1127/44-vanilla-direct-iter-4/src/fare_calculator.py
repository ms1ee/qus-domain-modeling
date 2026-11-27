"""Beijing Subway fare calculation.

Fare tiers (left-closed, right-open intervals, in meters):
    [0, 6000)       -> 3 yuan
    [6000, 12000)   -> 4 yuan
    [12000, 22000)  -> 5 yuan
    [22000, 32000)  -> 6 yuan
    >= 32000        -> 7 yuan + 1 yuan per additional full 20 km
"""

import math

# (upper bound in meters, exclusive) -> fare
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
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError(f"Distance must be a number, got {distance!r}")
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("Distance must be a finite number")
    if distance < 0:
        raise FareCalculationError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance in meters.

    Fractional distances are rounded up to the next whole meter.
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper, fare in FARE_TIERS:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_BASE_DISTANCE) // EXTENDED_STEP


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes (1.5 min/km + 5 min/transfer)."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        raise FareCalculationError("Transfer count must be non-negative")
    return float(distance / 1000.0 * MINUTES_PER_KM
                 + transfer_count * MINUTES_PER_TRANSFER)
