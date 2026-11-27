"""Beijing Subway fare calculation."""

import math

# (upper bound in meters, fare, inclusive upper bound?)
FARE_TABLE = [
    (6000, 3, True),
    (12000, 4, True),
    (22000, 5, False),
    (32000, 6, True),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 6
EXTENDED_STEP = 20000


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be finite")
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    d = math.ceil(distance)
    for upper, fare, inclusive in FARE_TABLE:
        if d < upper or (inclusive and d == upper):
            return fare
    extra = d - EXTENDED_BASE_DISTANCE
    return EXTENDED_BASE_FARE + math.ceil(extra / EXTENDED_STEP)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km plus 5 min per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("Distance and transfer count must be non-negative")
    return float(distance) / 1000.0 * 1.5 + transfer_count * 5.0
