"""Fare calculation."""
import math


class FareTier:
    def __init__(self, min_distance, max_distance, price):
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.price = price


FARE_TIERS = [FareTier(0, 6, 3), FareTier(6, 12, 4), FareTier(12, 22, 5), FareTier(22, 32, 6)]


def Sum_money(distance):
    """Fare in yuan for a distance in meters (fractions of km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0)
    for t in FARE_TIERS:
        if km <= t.max_distance:
            return t.price
    return 6 + math.ceil((km - 32) / 20.0)


class FareCalculator:
    def calculate(self, distance):
        return Sum_money(distance)


def calculate_estimated_time(distance, transfer_count):
    """Minutes: 1.5 per km plus 5 per transfer."""
    return distance / 1000.0 * 1.5 + 5.0 * transfer_count
