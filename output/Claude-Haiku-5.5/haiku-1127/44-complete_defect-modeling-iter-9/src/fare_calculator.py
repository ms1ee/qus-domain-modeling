"""Beijing Subway fare calculation based on travelled distance."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class FareRule:
    """A distance tier of the fare structure."""

    tier_name: str
    min_distance_km: float
    max_distance_km: Optional[float]
    fare_yuan: int
    increment_yuan: int = 0
    increment_distance_km: float = 0.0


# Beijing Subway fare structure (distances are ceiling-rounded to whole kilometers).
FARE_RULES: Tuple[FareRule, ...] = (
    FareRule("Base tier", 0.0, 6.0, 3),
    FareRule("Progressive tier 6-12 km", 6.0, 12.0, 4),
    FareRule("Progressive tier 12-22 km", 12.0, 22.0, 5),
    FareRule("Progressive tier 22-32 km", 22.0, 32.0, 6),
    FareRule("Extended tier over 32 km", 32.0, None, 6, 1, 20.0),
)

METERS_PER_KM = 1000.0
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 3.0


def Sum_money(distance: float) -> int:
    """Return the fare in yuan for a travelled distance given in meters.

    Fractional kilometers are rounded up (ceiling). Distances up to 6 km cost
    3 yuan; each tier above adds the tier fare; beyond 32 km every further
    20 km (or part thereof) adds 1 yuan.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or distance < 0:
        raise ValueError("distance must be a non-negative number of meters")

    km = math.ceil(distance / METERS_PER_KM)
    for rule in FARE_RULES:
        if rule.max_distance_km is None:
            continue
        if km <= rule.max_distance_km:
            return rule.fare_yuan

    extended = FARE_RULES[-1]
    extra_km = km - extended.min_distance_km
    steps = math.ceil(extra_km / extended.increment_distance_km)
    return int(extended.fare_yuan + steps * extended.increment_yuan)


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes for a distance in meters and a number of transfers."""
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    riding_minutes = (distance / METERS_PER_KM) / AVERAGE_SPEED_KMH * 60.0
    return round(riding_minutes + transfer_count * TRANSFER_TIME_MINUTES, 2)
