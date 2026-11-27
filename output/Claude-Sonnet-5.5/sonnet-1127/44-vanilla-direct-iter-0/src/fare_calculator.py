"""Fare calculation."""
import math


def Sum_money(distance):
    """Fare in yuan for a distance in meters (left-closed, right-open tiers)."""
    if distance is None or isinstance(distance, bool):
        raise ValueError("invalid distance")
    d = float(distance)
    if d != d or d < 0:
        raise ValueError("invalid distance")
    d = math.ceil(d)
    if d < 6000:
        return 3
    if d < 12000:
        return 4
    if d < 22000:
        return 5
    if d < 32000:
        return 6
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Minutes: 1.5 per km plus 5 per transfer."""
    return distance / 1000.0 * 1.5 + transfer_count * 5.0
