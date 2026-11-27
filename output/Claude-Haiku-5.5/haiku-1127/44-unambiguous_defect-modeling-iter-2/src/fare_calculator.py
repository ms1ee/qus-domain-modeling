"""Beijing Subway fare calculation.

Fare structure (distances in meters, boundaries inclusive at the lower end)::

    [0, 6000)          3 yuan
    [6000, 12000)      4 yuan
    [12000, 22000)     5 yuan
    [22000, 32000)     6 yuan
    [32000, ...)       7 yuan, plus 1 yuan for every further 20 km
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FareRule:
    """A distance band of the fare structure.

    Attributes:
        minDistance: Inclusive lower bound in meters.
        maxDistance: Exclusive upper bound in meters, or None for open-ended bands.
        baseFare: Fare in yuan at the lower bound of the band.
        increment: Yuan added for each full ``incrementInterval`` beyond the lower bound.
        incrementInterval: Interval in meters for the increment (0 for flat fares).
    """

    minDistance: float
    maxDistance: Optional[float]
    baseFare: int
    increment: int = 0
    incrementInterval: float = 0.0

    def contains(self, meters):
        """Return True if ``meters`` falls inside this band."""
        if meters < self.minDistance:
            return False
        return self.maxDistance is None or meters < self.maxDistance

    def fare_for(self, meters):
        """Return the fare in yuan for a distance inside this band."""
        if self.increment <= 0 or self.incrementInterval <= 0:
            return self.baseFare
        steps = math.floor((meters - self.minDistance) / self.incrementInterval)
        return self.baseFare + steps * self.increment


FARE_RULES = (
    FareRule(minDistance=0.0, maxDistance=6000.0, baseFare=3),
    FareRule(minDistance=6000.0, maxDistance=12000.0, baseFare=4),
    FareRule(minDistance=12000.0, maxDistance=22000.0, baseFare=5),
    FareRule(minDistance=22000.0, maxDistance=32000.0, baseFare=6),
    FareRule(minDistance=32000.0, maxDistance=None, baseFare=7, increment=1, incrementInterval=20000.0),
)

AVERAGE_SPEED_KMH = 35.0          # average operating speed including station dwell
BOARDING_OVERHEAD_MINUTES = 3.0   # waiting and boarding overhead for a journey
TRANSFER_TIME_MINUTES = 4.0       # walking and waiting time per transfer


@dataclass(frozen=True)
class Fare:
    """A monetary fare result."""

    amount: int
    currency: str = "CNY"


def _validate_distance(distance):
    """Validate a distance in meters and return it as a float."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number, got {type(distance).__name__}")
    value = float(distance)
    if math.isnan(value) or math.isinf(value) or value < 0:
        raise ValueError(f"Distance must be a finite non-negative number, got {distance}")
    return value


def get_fare_rule(distance):
    """Return the ``FareRule`` applicable to a distance in meters."""
    meters = math.ceil(_validate_distance(distance))
    for rule in FARE_RULES:
        if rule.contains(meters):
            return rule
    raise ValueError(f"No fare rule covers distance {distance}")  # pragma: no cover


def Sum_money(distance):
    """Calculate the subway fare in yuan for a distance in meters.

    Fractional distances are rounded up to the next whole meter before the
    band lookup, so boundaries behave as documented (6000 m -> 4 yuan,
    12000 m -> 5 yuan, 22000 m -> 6 yuan, 32000 m -> 7 yuan).

    Args:
        distance: Travel distance in meters.

    Returns:
        int: Fare in yuan.
    """
    meters = math.ceil(_validate_distance(distance))
    rule = get_fare_rule(meters)
    return int(rule.fare_for(meters))


class FareCalculator:
    """Object wrapper around the fare structure."""

    def __init__(self, rules=FARE_RULES, rounding_policy="ceil"):
        self.rules = tuple(rules)
        self.roundingPolicy = rounding_policy

    def calculate(self, distance):
        """Return a ``Fare`` for the given distance in meters."""
        return Fare(amount=Sum_money(distance), currency="CNY")


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    The estimate combines in-vehicle time (distance at average speed), a fixed
    boarding overhead and a fixed penalty per transfer.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers on the journey.

    Returns:
        float: Estimated time in minutes, rounded to one decimal place.
    """
    meters = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    ride_minutes = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_OVERHEAD_MINUTES + ride_minutes + transfer_count * TRANSFER_TIME_MINUTES
    return round(total, 1)
