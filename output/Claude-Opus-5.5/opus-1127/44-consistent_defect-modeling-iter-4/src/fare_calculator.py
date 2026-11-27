"""
Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometers):
  0-6 km   : 3 yuan  (6 km inclusive)
  6-12 km  : 4 yuan  (12 km inclusive)
  12-22 km : 5 yuan  (22 km inclusive)
  22-32 km : 6 yuan  (32 km inclusive)
  > 32 km  : +1 yuan for every additional 20 km (or part thereof)
"""

import math

# (upper bound in km, inclusive; fare in yuan)
FARE_TIERS = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_KM = 20
EXTENDED_INCREMENT_FARE = 1

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def Sum_money(distance):
    """Return the fare (yuan) for a distance in meters."""
    if distance is None:
        raise ValueError("Distance must not be None")
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid distance: {distance!r}")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError(f"Invalid distance: {distance!r}")
    km = math.ceil(distance / 1000.0)
    for upper, fare in FARE_TIERS:
        if km <= upper:
            return fare
    extra = km - EXTENDED_BASE_KM
    return EXTENDED_BASE_FARE + EXTENDED_INCREMENT_FARE * math.ceil(extra / EXTENDED_INCREMENT_KM)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km + 5 min per transfer."""
    if distance is None or distance < 0:
        raise ValueError(f"Invalid distance: {distance!r}")
    transfer_count = max(0, transfer_count or 0)
    return float(distance) / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
