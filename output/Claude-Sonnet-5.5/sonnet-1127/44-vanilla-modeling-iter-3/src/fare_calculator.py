"""Fare and time estimation."""
import math

FARE_TIERS = [(0, 6000, 3), (6000, 12000, 4), (12000, 22000, 5), (22000, 32000, 6)]


def Sum_money(distance):
    """Fare in yuan for a distance in meters (left-closed, right-open tiers)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    d = math.ceil(distance)
    for lo, hi, price in FARE_TIERS:
        if lo <= d < hi:
            return price
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Minutes: 1.5 per km plus 5 per transfer. distance in meters."""
    return distance / 1000.0 * 1.5 + transfer_count * 5
