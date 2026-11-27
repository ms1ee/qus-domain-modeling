"""Beijing Subway fare calculation and travel time estimation."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FareRule:
    """A distance tier with its fixed fare (kilometers, yuan)."""

    min_distance_km: float
    max_distance_km: float
    fare: int


# Beijing Subway basic fare tiers. Beyond the last tier, the fare grows by 1 yuan
# for every additional extension interval.
FARE_RULES: List[FareRule] = [
    FareRule(0.0, 6.0, 3),
    FareRule(6.0, 12.0, 4),
    FareRule(12.0, 22.0, 5),
    FareRule(22.0, 32.0, 6),
]

# Average operating speed used for time estimation (km/h).
AVERAGE_SPEED_KMH = 35.0
# Extra time per transfer (minutes).
TRANSFER_TIME_MIN = 5.0
# Fixed boarding/alighting time for the whole journey (minutes).
BOARDING_TIME_MIN = 2.0

_EPSILON = 1e-9


class FareCalculator:
    """Computes fares from distances in meters according to the tiered fare structure."""

    def __init__(
        self,
        rules: Optional[List[FareRule]] = None,
        ceiling_rounding: bool = True,
        extension_interval_km: int = 20,
    ) -> None:
        self.rules = list(rules) if rules is not None else list(FARE_RULES)
        if not self.rules:
            raise ValueError("at least one fare rule is required")
        if extension_interval_km <= 0:
            raise ValueError("extension_interval_km must be positive")
        self.ceiling_rounding = ceiling_rounding
        self.extension_interval_km = extension_interval_km

    def calculate(self, distance_m: float) -> int:
        """Return the fare in yuan for a distance given in meters.

        Fractional kilometers are rounded up (ceiling) when ``ceiling_rounding`` is enabled,
        so that any distance beyond a tier boundary is charged at the next tier.
        """
        if isinstance(distance_m, bool) or not isinstance(distance_m, (int, float)):
            raise ValueError("distance must be a number of meters")
        if math.isnan(distance_m) or math.isinf(distance_m):
            raise ValueError("distance must be a finite number")
        if distance_m < 0:
            raise ValueError("distance must be non-negative")

        km = distance_m / 1000.0
        if self.ceiling_rounding:
            km = float(math.ceil(km - _EPSILON))
            if km < 1.0:
                km = 1.0 if distance_m > 0 else 0.0

        for rule in self.rules:
            if km <= rule.max_distance_km + _EPSILON:
                return rule.fare

        last = self.rules[-1]
        extra_km = km - last.max_distance_km
        steps = math.ceil(extra_km / self.extension_interval_km - _EPSILON)
        return last.fare + max(steps, 0)


_DEFAULT_CALCULATOR = FareCalculator()


def Sum_money(distance: float) -> int:
    """Return the Beijing Subway fare in yuan for ``distance`` meters."""
    return _DEFAULT_CALCULATOR.calculate(distance)


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes for ``distance`` meters with ``transfer_count`` transfers."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
        raise ValueError("distance must be a non-negative number of meters")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    travel_min = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = travel_min + transfer_count * TRANSFER_TIME_MIN + BOARDING_TIME_MIN
    return round(float(total), 1)
