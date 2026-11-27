"""Fare calculation based on the Beijing Subway fare structure."""

import math
from dataclasses import dataclass
from typing import Optional

CURRENCY = "CNY"

# Average operating speed used for time estimates (km/h).
AVERAGE_SPEED_KMH = 35.0
# Fixed boarding / waiting allowance (minutes).
BOARDING_MINUTES = 3.0
# Time cost of each transfer (minutes).
TRANSFER_MINUTES = 5.0


class FareError(ValueError):
    """Raised when a fare cannot be calculated from the given input."""


@dataclass(frozen=True)
class FareTier:
    """A distance band of the fare structure.

    Attributes:
        min_distance_meters: inclusive lower bound.
        max_distance_meters: exclusive upper bound (None for open-ended tier).
        base_fare: fare in yuan at the lower bound of the tier.
        increment_yuan: yuan added for every ``step_meters`` beyond the lower bound.
        step_meters: length of the increment step (0 means no increment).
    """

    min_distance_meters: float
    max_distance_meters: Optional[float]
    base_fare: int
    increment_yuan: int = 0
    step_meters: float = 0.0


@dataclass(frozen=True)
class Fare:
    """Fare result."""

    amount_yuan: int
    currency: str = CURRENCY


DEFAULT_TIERS = (
    FareTier(0, 6000, 3),
    FareTier(6000, 12000, 4),
    FareTier(12000, 22000, 5),
    FareTier(22000, 32000, 6),
    FareTier(32000, None, 7, increment_yuan=1, step_meters=20000),
)


class FareCalculator:
    """Converts a travel distance in meters into a fare using a tier table.

    Fractional distances are rounded up to whole meters ("ceil" rule) before
    the tier lookup, so any distance inside a tier's range is charged at that
    tier's fare, and boundary values follow the PRD (6000 m -> 4 yuan, etc.).
    """

    def __init__(self, tiers=DEFAULT_TIERS, rounding_rule="ceil"):
        if rounding_rule != "ceil":
            raise ValueError("Only the 'ceil' rounding rule is supported")
        self.tiers = tuple(tiers)
        self.rounding_rule = rounding_rule

    @staticmethod
    def _normalize_distance(distance):
        """Validate the distance and round it up to whole meters."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise FareError(f"Distance must be a number, got {type(distance).__name__}")
        if math.isnan(distance) or math.isinf(distance):
            raise FareError("Distance must be a finite number")
        if distance < 0:
            raise FareError("Distance must be non-negative")
        return math.ceil(distance)

    def _tier_for(self, distance):
        """Return the tier that contains ``distance`` (in whole meters)."""
        for tier in self.tiers:
            above_min = distance >= tier.min_distance_meters
            below_max = tier.max_distance_meters is None or distance < tier.max_distance_meters
            if above_min and below_max:
                return tier
        raise FareError(f"No fare tier covers distance {distance} m")

    def calculate(self, distance_meters):
        """Return the Fare for a distance in meters."""
        distance = self._normalize_distance(distance_meters)
        tier = self._tier_for(distance)
        amount = tier.base_fare
        if tier.step_meters and tier.increment_yuan:
            steps = int((distance - tier.min_distance_meters) // tier.step_meters)
            amount += steps * tier.increment_yuan
        return Fare(amount_yuan=int(amount), currency=CURRENCY)


_DEFAULT_CALCULATOR = FareCalculator()


def Sum_money(distance):
    """Return the fare in yuan (int) for a distance given in meters."""
    try:
        return _DEFAULT_CALCULATOR.calculate(distance).amount_yuan
    except FareError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapping
        raise FareError(f"Fare calculation failed: {exc}") from exc


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    The estimate is the fixed boarding allowance, plus riding time at the
    average operating speed, plus a fixed cost per transfer.

    Args:
        distance: travel distance in meters.
        transfer_count: number of transfers.

    Returns:
        estimated time in minutes, rounded to one decimal place.
    """
    if distance < 0:
        raise FareError("Distance must be non-negative")
    if transfer_count < 0:
        raise FareError("Transfer count must be non-negative")
    ride_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_MINUTES + ride_minutes + transfer_count * TRANSFER_MINUTES
    return round(total, 1)
