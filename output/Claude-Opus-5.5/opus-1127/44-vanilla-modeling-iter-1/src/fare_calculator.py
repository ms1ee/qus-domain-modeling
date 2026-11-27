"""Beijing Subway fare calculation.

Tiers (left-closed, right-open intervals, distance in meters):
    [0, 6000)      -> 3 yuan
    [6000, 12000)  -> 4 yuan
    [12000, 22000) -> 5 yuan
    [22000, 32000) -> 6 yuan
    >= 32000       -> 7 yuan + 1 yuan per additional full 20 km
"""

import math

# (lower bound inclusive, upper bound exclusive, fare in yuan)
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


class FareCalculationError(ValueError):
    """Raised when a fare cannot be computed for a distance."""


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters.

    Fractional distances are rounded up to the next whole meter.
    """
    if isinstance(distance, bool):
        raise FareCalculationError("Distance must be a number")
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Invalid distance: {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise FareCalculationError(f"Invalid distance: {distance!r}")
    if value < 0:
        raise FareCalculationError("Distance cannot be negative")
    meters = math.ceil(value)
    for low, high, fare in FARE_TIERS:
        if low <= meters < high:
            return fare
    extra = (meters - EXTENDED_START) // EXTENDED_INCREMENT_DISTANCE
    return EXTENDED_BASE_FARE + extra * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km plus 5 min/transfer."""
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    transfers = max(0, transfer_count)
    return float(distance / 1000.0 * MINUTES_PER_KM + transfers * MINUTES_PER_TRANSFER)
