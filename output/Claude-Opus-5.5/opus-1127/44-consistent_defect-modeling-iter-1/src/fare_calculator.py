"""Beijing Subway fare calculation.

Fare tiers (distance in meters):
    0      < d <= 6000   : 3 yuan
    6000   < d <= 12000  : 4 yuan
    12000  < d <  22000  : 5 yuan
    22000 <= d <= 32000  : 6 yuan
    d > 32000            : 6 yuan + 1 yuan per (started) additional 20 km
"""

import math

# Fare structure: (upper bound in meters, inclusive flag, fare in yuan)
FARE_TIERS = [
    (6000, True, 3),
    (12000, True, 4),
    (22000, False, 5),
    (32000, True, 6),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 6
EXTENDED_STEP = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Return the fare (yuan, int) for a travel distance in meters.

    Fractional distances are rounded up to the next whole meter.
    :raises ValueError: for negative or non-numeric distances
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number")
    if isinstance(distance, float) and (math.isnan(distance) or math.isinf(distance)):
        raise ValueError("Distance must be finite")
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    d = int(math.ceil(distance))
    for upper, inclusive, fare in FARE_TIERS:
        if d < upper or (inclusive and d == upper):
            return fare
    extra = d - EXTENDED_BASE_DISTANCE
    if extra <= 0:
        return EXTENDED_BASE_FARE
    return EXTENDED_BASE_FARE + int(math.ceil(extra / EXTENDED_STEP))


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes.

    About 1.5 minutes per kilometer plus 5 minutes per transfer.
    """
    if distance is None or distance < 0:
        raise ValueError("Distance cannot be negative")
    transfer_count = max(0, int(transfer_count or 0))
    return float(distance) / 1000.0 * MINUTES_PER_KM + \
        transfer_count * MINUTES_PER_TRANSFER
