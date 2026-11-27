"""Beijing Subway fare calculation.

Fare structure (distance in kilometres, right-closed intervals):
    0  - 6   : 3 yuan
    6  - 12  : 4 yuan
    12 - 22  : 5 yuan
    22 - 32  : 6 yuan
    > 32     : +1 yuan for every additional 20 km (rounded up)
"""

import math

# (upper bound in meters, fare)
FARE_TIERS = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Return the fare (yuan, int) for a travel distance given in meters."""
    if distance is None:
        raise ValueError("Distance must not be None")
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid distance: {distance!r}")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError(f"Invalid distance: {distance!r}")
    for upper, fare in FARE_TIERS:
        if distance <= upper:
            return fare
    extra = math.ceil((distance - EXTENDED_BASE_DISTANCE) / EXTENDED_INCREMENT_DISTANCE)
    return EXTENDED_BASE_FARE + extra * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes: 1.5 min/km plus 5 min per transfer."""
    if distance is None or distance < 0:
        raise ValueError(f"Invalid distance: {distance!r}")
    transfer_count = transfer_count or 0
    if transfer_count < 0:
        raise ValueError(f"Invalid transfer count: {transfer_count!r}")
    return distance / 1000 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
