"""Fare calculation."""
import math


def Sum_money(distance):
    """Fare in yuan for a distance in meters (fractions rounded up)."""
    if distance < 0:
        raise ValueError("distance must be non-negative")
    d = math.ceil(distance)
    if d <= 6000:
        return 3
    if d <= 12000:
        return 4
    if d < 22000:
        return 5
    if d <= 32000:
        return 6
    return 7 + (d - 32001) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Minutes: 1.5 per km plus 5 per transfer."""
    return distance / 1000.0 * 1.5 + 5.0 * transfer_count
