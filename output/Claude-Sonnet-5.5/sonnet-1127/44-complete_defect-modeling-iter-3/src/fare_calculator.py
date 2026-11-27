"""Fare and time estimation."""
import math

FARE_TIERS = [(0, 6, 3), (6, 12, 4), (12, 22, 5), (22, 32, 6)]


def Sum_money(distance):
    """Fare in yuan for a distance in meters (km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0 - 1e-9)
    for lo, hi, fare in FARE_TIERS:
        if km <= hi:
            return fare
    return 6 + int(math.ceil((km - 32) / 20.0))


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: ~35 km/h average speed plus 5 min per transfer."""
    return round(distance / 1000.0 / 35.0 * 60.0 + 5.0 * transfer_count, 1)
