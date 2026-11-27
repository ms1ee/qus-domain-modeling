"""Fare calculation."""
import math

FARE_TIERS = [(6, 3), (12, 4), (22, 5), (32, 6)]
EXTENDED_STEP_KM = 20
EXTENDED_STEP_FARE = 1
AVG_SPEED_KMH = 35.0
TRANSFER_MINUTES = 5.0


def Sum_money(distance):
    """Fare in yuan for a distance in meters (km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0)
    for limit, fare in FARE_TIERS:
        if km <= limit:
            return fare
    return FARE_TIERS[-1][1] + math.ceil((km - 32) / EXTENDED_STEP_KM) * EXTENDED_STEP_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes for distance in meters."""
    return round(distance / 1000.0 / AVG_SPEED_KMH * 60.0 + transfer_count * TRANSFER_MINUTES, 1)
