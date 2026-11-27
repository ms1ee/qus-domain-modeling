"""Beijing Subway fare structure (distance based, left-closed intervals)."""

import math

# (lower bound inclusive, upper bound exclusive, fare) in meters / yuan
FARE_TIERS = [
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
]
EXTENDED_START = 32000
EXTENDED_STEP = 20000
EXTENDED_BASE_FARE = 7

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _check_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a number" % name)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be a finite number" % name)
    if value < 0:
        raise ValueError("%s must be non-negative" % name)


def Sum_money(distance):
    """Return the fare (yuan) for a travel distance given in meters.

    Fractional distances are rounded up to the next whole meter; tier
    boundaries belong to the higher tier (6000 m -> 4 yuan, ...).
    """
    _check_number(distance, "distance")
    d = math.ceil(distance)
    for low, high, fare in FARE_TIERS:
        if low <= d < high:
            return fare
    return EXTENDED_BASE_FARE + (d - EXTENDED_START) // EXTENDED_STEP


calculate_fare = Sum_money


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes (1.5 min/km + 5 min per transfer)."""
    _check_number(distance, "distance")
    _check_number(transfer_count, "transfer_count")
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
