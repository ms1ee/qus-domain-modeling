"""Fare calculation according to the Beijing Subway fare structure.

Tiers (left-closed, right-open intervals, distance in meters):
    [0, 6000)       -> 3 yuan
    [6000, 12000)   -> 4 yuan
    [12000, 22000)  -> 5 yuan
    [22000, 32000)  -> 6 yuan
    >= 32000        -> 7 yuan + 1 yuan per additional full 20 km
"""

import math
import numbers
from dataclasses import dataclass


class FareCalculationError(ValueError):
    """Raised when a fare cannot be calculated."""


@dataclass(frozen=True)
class FareTier:
    min_distance: int
    max_distance: int
    fare: int
    tier_type: str


FARE_TIERS = [
    FareTier(0, 6000, 3, "basic"),
    FareTier(6000, 12000, 4, "progressive"),
    FareTier(12000, 22000, 5, "progressive"),
    FareTier(22000, 32000, 6, "progressive"),
]

EXTENDED_THRESHOLD = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
        raise FareCalculationError("Distance must be a number, got {!r}".format(distance))
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("Distance must be a finite number")
    if distance < 0:
        raise FareCalculationError("Distance cannot be negative")


def Sum_money(distance) -> int:
    """Return the fare (yuan) for a distance given in meters.

    Fractional distances are rounded up to the next whole meter.
    """
    _validate_distance(distance)
    meters = math.ceil(distance)
    for tier in FARE_TIERS:
        if tier.min_distance <= meters < tier.max_distance:
            return tier.fare
    extra = (meters - EXTENDED_THRESHOLD) // EXTENDED_INCREMENT_DISTANCE
    return int(EXTENDED_BASE_FARE + extra * EXTENDED_INCREMENT_FARE)


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated travel time in minutes (1.5 min/km, 5 min per transfer)."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, numbers.Real) \
            or transfer_count < 0:
        raise FareCalculationError("Transfer count must be a non-negative number")
    return float(distance / 1000.0 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)


class FareCalculator:
    """Object-oriented wrapper around the fare functions."""

    tiers = FARE_TIERS

    def calculate(self, distance) -> int:
        return Sum_money(distance)

    def estimated_time(self, distance, transfer_count) -> float:
        return calculate_estimated_time(distance, transfer_count)
