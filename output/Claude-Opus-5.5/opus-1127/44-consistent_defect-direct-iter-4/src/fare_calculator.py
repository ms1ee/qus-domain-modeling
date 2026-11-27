"""Beijing Subway fare calculation."""
import math

# Fare structure: (upper bound in meters, fare, upper bound inclusive?)
FARE_TIERS = [
    (6000, 3, True),
    (12000, 4, True),
    (22000, 5, False),
    (32000, 6, True),
]
EXTENDED_BASE_DISTANCE = 32000
EXTENDED_BASE_FARE = 6
EXTENDED_STEP = 20000

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def Sum_money(distance) -> int:
    """Return the fare (yuan) for a distance in meters."""
    if distance is None:
        raise ValueError("Distance must not be None")
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid distance: {distance!r}")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError(f"Invalid distance: {distance!r}")
    d = math.ceil(distance)
    for bound, fare, inclusive in FARE_TIERS:
        if d < bound or (inclusive and d == bound):
            return fare
    extra = d - EXTENDED_BASE_DISTANCE
    return EXTENDED_BASE_FARE + math.ceil(extra / EXTENDED_STEP)


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated travel time in minutes (1.5 min/km + 5 min/transfer)."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("Distance and transfer count must be non-negative")
    return distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
