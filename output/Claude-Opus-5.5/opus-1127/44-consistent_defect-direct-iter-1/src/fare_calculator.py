"""Beijing Subway fare calculation."""

import math

# (upper bound in meters, inclusive flag, fare)
FARE_TABLE = [
    (6000, True, 3),
    (12000, True, 4),
    (22000, False, 5),
    (32000, True, 6),
]
BASE_EXTENDED_FARE = 6
EXTENDED_START = 32000
EXTENDED_STEP = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _validate(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be finite")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance) -> int:
    """Return the fare (yuan) for a distance given in meters."""
    _validate(distance)
    d = math.ceil(distance)
    for upper, inclusive, fare in FARE_TABLE:
        if (inclusive and d <= upper) or (not inclusive and d < upper):
            return fare
    extra = math.ceil((d - EXTENDED_START) / EXTENDED_STEP)
    return BASE_EXTENDED_FARE + extra


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated travel time in minutes (distance in meters)."""
    _validate(distance)
    if transfer_count is None or transfer_count < 0:
        transfer_count = 0
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
