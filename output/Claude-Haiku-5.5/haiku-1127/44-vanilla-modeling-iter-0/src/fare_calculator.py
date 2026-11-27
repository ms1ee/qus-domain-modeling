"""
Fare calculation for the Beijing Subway.

Fare structure (distances are rounded up to a whole meter, and every
boundary value belongs to the next, higher tier, i.e. left-closed/right-open):

    [0, 6 km)        3 yuan
    [6 km, 12 km)    4 yuan
    [12 km, 22 km)   5 yuan
    [22 km, 32 km)   6 yuan
    [32 km, ...)     7 yuan, plus 1 yuan for every additional 20 km
                     (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Estimated travel time model.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


@dataclass(frozen=True)
class FareRule:
    """A distance band with its fare.

    Attributes:
        min_distance_m: Inclusive lower bound of the band, in meters.
        max_distance_m: Exclusive upper bound in meters, or None for the open-ended band.
        fare_yuan: Fare for the band (the base fare of the extended tier).
        increment_km: For the extended tier, the distance per extra yuan (in km).
    """

    min_distance_m: float
    max_distance_m: float | None
    fare_yuan: int
    increment_km: float = 0.0


# Fare table, ordered by distance. The last rule is the extended (open-ended) tier.
FARE_RULES: tuple[FareRule, ...] = (
    FareRule(0, 6000, 3),
    FareRule(6000, 12000, 4),
    FareRule(12000, 22000, 5),
    FareRule(22000, 32000, 6),
    FareRule(32000, None, 7, increment_km=20.0),
)


def Sum_money(distance: float) -> int:
    """Return the Beijing Subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters. Fractional distances are rounded up.

    Returns:
        The fare in yuan.

    Raises:
        TypeError: If the distance is not a real number.
        ValueError: If the distance is negative or not finite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    meters = int(math.ceil(distance))  # ceiling rounding for fractional distances
    for rule in FARE_RULES:
        if rule.max_distance_m is None:
            continue
        if rule.min_distance_m <= meters < rule.max_distance_m:
            return rule.fare_yuan

    # Extended tier: 7 yuan from 32 km, plus 1 yuan per full 20 km beyond that.
    extended = FARE_RULES[-1]
    step_m = extended.increment_km * 1000
    extra_steps = int((meters - extended.min_distance_m) // step_m)
    return extended.fare_yuan + extra_steps


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate the travel time in minutes.

    The estimate is about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated travel time in minutes.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
