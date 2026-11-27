"""Fare and time estimation."""
import math

FARE_TIERS = [(6, 3), (12, 4), (22, 5), (32, 6)]
AVERAGE_SPEED_KMH = 35.0
TRANSFER_MINUTES = 5.0


def Sum_money(distance):
    """Fare in yuan for a distance in meters (km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("Invalid distance: %r" % (distance,))
    km = math.ceil(distance / 1000.0)
    for limit, fare in FARE_TIERS:
        if km <= limit:
            return fare
    return 6 + int(math.ceil((km - 32) / 20.0))


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes for a distance in meters and number of transfers."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("Invalid distance or transfer count")
    return round(distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0 + transfer_count * TRANSFER_MINUTES, 1)
