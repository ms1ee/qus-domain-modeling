"""Fare calculation."""
import math


def Sum_money(distance):
    """Fare in yuan for a distance in meters (fractional km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0 - 1e-12)
    if km <= 6:
        return 3
    if km <= 12:
        return 4
    if km < 22:
        return 5
    if km <= 32:
        return 6
    return 7 + (km - 33) // 20


def calculate_estimated_time(distance, transfer_count):
    """Minutes: 1.5 per km plus 5 per transfer."""
    return distance / 1000.0 * 1.5 + transfer_count * 5.0
