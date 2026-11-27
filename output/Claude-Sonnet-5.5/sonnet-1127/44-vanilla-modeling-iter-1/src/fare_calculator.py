"""Fare and time estimation."""
import math

FARE_TIERS = [(6000, 3), (12000, 4), (22000, 5), (32000, 6)]


def Sum_money(distance):
    """Fare in yuan for distance in meters (left-closed, right-open tiers)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    d = math.ceil(distance)
    for limit, fare in FARE_TIERS:
        if d < limit:
            return fare
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Minutes: 1.5 per km plus 5 per transfer."""
    return distance / 1000.0 * 1.5 + transfer_count * 5


class FareCalculator:
    def calculate(self, distance):
        return Sum_money(distance)
