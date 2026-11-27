"""Fare calculation."""
import math


class FareTier:
    def __init__(self, min_distance, max_distance, price):
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.price = price


def Sum_money(distance):
    """Fare in yuan for a distance in meters (fractions round up to km)."""
    if distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000)
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
    return distance / 1000 * 1.5 + transfer_count * 5


class FareCalculator:
    def calculate(self, distance):
        return Sum_money(distance)
