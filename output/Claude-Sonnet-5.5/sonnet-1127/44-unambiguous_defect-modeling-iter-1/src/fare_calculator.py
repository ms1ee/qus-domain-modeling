"""Fare and time estimation."""
import math

FARE_TIERS = [(0, 6000, 3), (6000, 12000, 4), (12000, 22000, 5), (22000, 32000, 6)]


def Sum_money(distance):
    """Fare in yuan for a distance in meters."""
    if distance is None or distance < 0 or distance != distance:
        raise ValueError("Invalid distance: %r" % (distance,))
    d = int(math.ceil(distance))
    for lo, hi, fare in FARE_TIERS:
        if d < hi:
            return fare
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: ~35 km/h average, 5 min per transfer, 2 min boarding."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("Invalid arguments")
    return round(distance / 1000.0 / 35.0 * 60.0 + transfer_count * 5 + 2, 1)
