"""
Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometres):
    0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan,
    above 32 km: +1 yuan for every (started) 20 km.
"""

import math
from dataclasses import dataclass, field
from typing import List

# (min_km exclusive, max_km inclusive, fare yuan)
FARE_TIERS = [(0, 6, 3), (6, 12, 4), (12, 22, 5), (22, 32, 6)]
EXTENDED_INCREMENT_KM = 20
EXTENDED_INCREMENT_YUAN = 1

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def _validate_number(value, name):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if isinstance(value, float) and math.isnan(value):
        raise ValueError(f"{name} must be a valid number")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def distance_to_km_ceiling(distance):
    """Convert meters to whole kilometres, rounding up."""
    _validate_number(distance, "distance")
    if isinstance(distance, int):
        return -(-distance // 1000)
    return int(math.ceil(distance / 1000.0))


@dataclass
class FareTier:
    min_km: int
    max_km: int
    fare_yuan: int


@dataclass
class FareStructure:
    tiers: List[FareTier] = field(default_factory=lambda: [FareTier(*t) for t in FARE_TIERS])
    extended_increment_km: int = EXTENDED_INCREMENT_KM
    extended_increment_yuan: int = EXTENDED_INCREMENT_YUAN


class FareCalculator:
    """Distance-to-fare conversion based on a FareStructure."""

    def __init__(self, structure=None, round_up_distance=True):
        self.structure = structure or FareStructure()
        self.round_up_distance = round_up_distance

    def calculate(self, distance):
        _validate_number(distance, "distance")
        km = distance_to_km_ceiling(distance) if self.round_up_distance else distance / 1000.0
        tiers = self.structure.tiers
        for tier in tiers:
            if km <= tier.max_km:
                return tier.fare_yuan
        last = tiers[-1]
        extra = km - last.max_km
        steps = int(math.ceil(extra / float(self.structure.extended_increment_km)))
        return last.fare_yuan + steps * self.structure.extended_increment_yuan


_DEFAULT_CALCULATOR = FareCalculator()


def Sum_money(distance):
    """Return the fare in yuan for a distance given in meters."""
    return _DEFAULT_CALCULATOR.calculate(distance)


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance (meters) and transfers."""
    _validate_number(distance, "distance")
    _validate_number(transfer_count, "transfer_count")
    riding = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return float(riding + transfer_count * TRANSFER_TIME_MINUTES)
