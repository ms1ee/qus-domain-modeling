"""Beijing Subway fare calculation.

Tiers (left-closed, right-open intervals, distances in meters):
    [0, 6000)        -> 3 yuan
    [6000, 12000)    -> 4 yuan
    [12000, 22000)   -> 5 yuan
    [22000, 32000)   -> 6 yuan
    [32000, ...)     -> 7 yuan, plus 1 yuan for every further 20 km
Fractional distances are rounded up (ceiling) before tier lookup.
"""

import math
from dataclasses import dataclass
from typing import Optional

METERS_PER_KM = 1000
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


@dataclass(frozen=True)
class FareTier:
    """A distance band and its fare.

    Attributes:
        min_distance: Inclusive lower bound in meters.
        max_distance: Exclusive upper bound in meters, or None if open-ended.
        fare: Fare in yuan.
    """

    min_distance: float
    max_distance: Optional[float]
    fare: int


DEFAULT_TIERS = (
    FareTier(0, 6000, 3),
    FareTier(6000, 12000, 4),
    FareTier(12000, 22000, 5),
    FareTier(22000, 32000, 6),
)


class FareCalculator:
    """Maps a travel distance to a fare using bounded tiers plus an extension rule."""

    def __init__(self, tiers=None, extension_step_km=20):
        tier_list = list(tiers if tiers is not None else DEFAULT_TIERS)
        if not tier_list:
            raise ValueError("at least one fare tier is required")
        for previous, current in zip(tier_list, tier_list[1:]):
            if previous.max_distance != current.min_distance:
                raise ValueError("fare tiers must be contiguous")
        if tier_list[-1].max_distance is None:
            raise ValueError("the last fare tier must be bounded (extension starts there)")
        if extension_step_km <= 0:
            raise ValueError("extension_step_km must be positive")
        self.tiers = tier_list
        self.extension_step_km = extension_step_km

    def calculate(self, distance_m):
        """Return the fare in yuan for a distance in meters.

        Raises:
            ValueError: If the distance is None, negative, or not finite.
        """
        if distance_m is None or not math.isfinite(distance_m) or distance_m < 0:
            raise ValueError(f"invalid distance: {distance_m!r}")
        meters = math.ceil(distance_m)
        for tier in self.tiers:
            if meters >= tier.min_distance and (tier.max_distance is None or meters < tier.max_distance):
                return tier.fare
        # Beyond the last bounded tier: extended fare.
        last = self.tiers[-1]
        step_m = self.extension_step_km * METERS_PER_KM
        steps = int((meters - last.max_distance) // step_m)
        return last.fare + 1 + steps


_DEFAULT_CALCULATOR = FareCalculator()


def Sum_money(distance):
    """Return the Beijing Subway fare (yuan) for ``distance`` meters."""
    return _DEFAULT_CALCULATOR.calculate(distance)


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Approximately 1.5 minutes per kilometer plus 5 minutes per transfer.

    Args:
        distance: Distance in meters.
        transfer_count: Number of transfers.
    """
    if distance is None or not math.isfinite(distance) or distance < 0:
        raise ValueError(f"invalid distance: {distance!r}")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / METERS_PER_KM) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
