"""Fare and time estimation."""
import math

FARE_TIERS = [(6000, 3), (12000, 4), (22000, 5), (32000, 6)]


def Sum_money(distance):
    """Fare in yuan for distance in meters."""
    if distance is None or distance != distance or distance < 0:
        raise ValueError("invalid distance: %r" % (distance,))
    d = math.ceil(distance)
    for limit, fare in FARE_TIERS:
        if d < limit:
            return fare
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: 35 km/h average plus 5 min per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("negative input")
    return distance / 1000.0 / 35.0 * 60.0 + 5.0 * transfer_count
