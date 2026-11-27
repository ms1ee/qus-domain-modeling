"""Beijing Subway fare calculation and trip time estimation.

Fare structure (distances in meters, left-closed / right-open intervals):
    0 - 6 km      : 3 yuan
    6 - 12 km     : 4 yuan
    12 - 22 km    : 5 yuan
    22 - 32 km    : 6 yuan
    >= 32 km      : 7 yuan, +1 yuan for every additional 20 km
Fractional distances are rounded up to the next whole meter before lookup.
"""

import math
from dataclasses import dataclass
from typing import Optional

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


@dataclass(frozen=True)
class FareTier:
    """One fare tier.

    Attributes:
        name: human-readable tier name.
        min_distance_m: inclusive lower bound in meters.
        max_distance_m: exclusive upper bound in meters, None for open-ended.
        price: base price in yuan for the tier.
        increment_distance_m: distance covered per extra yuan (0 if fixed price).
    """

    name: str
    min_distance_m: float
    max_distance_m: Optional[float]
    price: int
    increment_distance_m: float


FARE_TIERS = (
    FareTier("basic", 0, 6000, 3, 0),
    FareTier("progressive-6km", 6000, 12000, 4, 0),
    FareTier("progressive-12km", 12000, 22000, 5, 0),
    FareTier("progressive-22km", 22000, 32000, 6, 0),
    FareTier("extended", 32000, None, 7, 20000),
)


def _normalize_distance(distance):
    """Validate a distance and round it up to whole meters."""
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Distance must be a number, got {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Distance must be a finite number")
    if value < 0:
        raise ValueError("Distance must not be negative")
    return math.ceil(value)


def Sum_money(distance):
    """Return the fare in yuan for a travel distance given in meters.

    Boundary values belong to the higher tier (e.g. 6000 m -> 4 yuan).
    """
    meters = _normalize_distance(distance)
    for tier in FARE_TIERS:
        if tier.max_distance_m is None:
            if meters >= tier.min_distance_m:
                steps = int((meters - tier.min_distance_m) // tier.increment_distance_m)
                return tier.price + steps
        elif tier.min_distance_m <= meters < tier.max_distance_m:
            return tier.price
    raise ValueError("No fare tier matches the given distance")


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: travel distance in meters.
        transfer_count: number of transfers.

    Returns:
        Estimated minutes: about 1.5 min per km plus about 5 min per transfer.
    """
    meters = max(0.0, float(distance))
    km = meters / 1000.0
    return float(km * MINUTES_PER_KM + max(0, int(transfer_count)) * MINUTES_PER_TRANSFER)
