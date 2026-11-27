"""Fare and time calculation."""
import math

FARE_TIERS = [(6, 3), (12, 4), (22, 5), (32, 6)]


def Sum_money(distance):
    """Fare in yuan for a distance in meters (km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0 - 1e-9)
    for limit, fare in FARE_TIERS:
        if km <= limit:
            return fare
    return 6 + math.ceil((km - 32) / 20.0)


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: 35 km/h average speed plus 5 min per transfer."""
    return (distance / 1000.0) / 35.0 * 60.0 + transfer_count * 5.0
