"""Beijing Subway fare calculation.

Fare structure (distance in kilometers):
    [0, 6)   -> 3 yuan
    [6, 12)  -> 4 yuan
    [12, 22) -> 5 yuan
    [22, 32) -> 6 yuan
    >= 32    -> 7 yuan, plus 1 yuan for every further full 20 km
Fractional meters are rounded up before the tier lookup.
"""

import math
import numbers

# (exclusive upper bound in meters, fare in yuan)
FARE_TIERS = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_TIER_START = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP = 20000

AVERAGE_SPEED_KMH = 35.0
AVERAGE_SPEED_M_PER_MIN = AVERAGE_SPEED_KMH * 1000 / 60
TRANSFER_TIME_MINUTES = 5.0


class FareCalculationError(ValueError, TypeError):
    """Raised when a fare cannot be computed from the given distance."""


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
        raise FareCalculationError("Distance must be a number, got %r" % (distance,))
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("Distance must be finite, got %r" % (distance,))
    if distance < 0:
        raise FareCalculationError("Distance cannot be negative, got %r" % (distance,))


def Sum_money(distance):
    """Return the fare in yuan for a travel distance given in meters."""
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper, fare in FARE_TIERS:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_TIER_START) // EXTENDED_STEP


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Based on an average running speed of 35 km/h plus 5 minutes per transfer.
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, numbers.Real):
        raise FareCalculationError("Transfer count must be a number")
    if transfer_count < 0:
        raise FareCalculationError("Transfer count cannot be negative")
    minutes = distance / AVERAGE_SPEED_M_PER_MIN + transfer_count * TRANSFER_TIME_MINUTES
    return float(round(minutes, 1))


def format_fare(fare):
    return "Fare: %d yuan" % fare
