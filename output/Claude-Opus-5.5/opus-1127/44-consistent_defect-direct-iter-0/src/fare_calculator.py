"""Beijing Subway fare calculation."""

import math

# (upper bound in meters, inclusive flag, fare)
FARE_TABLE = [
    (6000, True, 3),
    (12000, True, 4),
    (22000, False, 5),
    (32000, True, 6),
]
EXTENDED_STEP = 20000   # meters per additional yuan beyond 32 km
EXTENDED_BASE = 32000


def Sum_money(distance):
    """Return the fare (yuan) for a distance in meters."""
    if distance is None:
        raise ValueError("Distance cannot be None")
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid distance: {distance!r}")
    if math.isnan(distance) or distance < 0:
        raise ValueError(f"Invalid distance: {distance}")
    distance = math.ceil(distance)
    for upper, inclusive, fare in FARE_TABLE:
        if (distance <= upper) if inclusive else (distance < upper):
            return fare
    extra = math.ceil((distance - EXTENDED_BASE) / EXTENDED_STEP)
    return 6 + extra


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: 1.5 min per km plus 5 min per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("Distance and transfer count must be non-negative")
    return round(distance / 1000.0 * 1.5 + transfer_count * 5, 2)
