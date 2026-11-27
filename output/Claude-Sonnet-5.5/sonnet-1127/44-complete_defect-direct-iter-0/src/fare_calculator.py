"""Fare and time estimation."""
import math

AVERAGE_SPEED_KMH = 35.0
TRANSFER_MINUTES = 5.0


def Sum_money(distance):
    """Fare in yuan for a distance in meters (distance rounded up to km)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0)
    if km <= 6:
        return 3
    if km <= 12:
        return 4
    if km <= 22:
        return 5
    if km <= 32:
        return 6
    return 6 + math.ceil((km - 32) / 20.0)


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes for a distance in meters."""
    return distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0 + transfer_count * TRANSFER_MINUTES
