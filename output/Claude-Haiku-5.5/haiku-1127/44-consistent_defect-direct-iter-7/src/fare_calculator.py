"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distances in meters, left-closed / right-open intervals):
    [0, 6000)          -> 3 yuan
    [6000, 12000)      -> 4 yuan
    [12000, 22000)     -> 5 yuan
    [22000, 32000)     -> 6 yuan
    [32000, 52000)     -> 7 yuan   (extended tier: +1 yuan per further 20 km)
    [52000, 72000)     -> 8 yuan
    ...
Fractional distances are rounded up (ceiling) to the next whole meter before
the tier is determined, so a boundary value always enters the next tier.
"""
from __future__ import annotations

import math
from typing import Tuple

MINUTES_PER_KM: float = 1.5
MINUTES_PER_TRANSFER: float = 5.0

# (lower bound in meters, fare in yuan) for the basic and progressive tiers.
BASE_FARE_TIERS: Tuple[Tuple[int, int], ...] = (
    (0, 3),
    (6000, 4),
    (12000, 5),
    (22000, 6),
)
EXTENDED_TIER_START: int = 32000
EXTENDED_TIER_FARE: int = 7
EXTENDED_STEP_METERS: int = 20000


def Sum_money(distance: float) -> int:
    """Return the fare in yuan for a trip of ``distance`` meters.

    Raises:
        ValueError: if the distance is negative or not a number.
    """
    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        raise ValueError("distance must be a number of meters")
    if distance != distance or distance < 0:  # NaN or negative
        raise ValueError("distance must be a non-negative number of meters")

    meters = math.ceil(distance)  # ceiling rounding of fractional distances

    if meters >= EXTENDED_TIER_START:
        return EXTENDED_TIER_FARE + (meters - EXTENDED_TIER_START) // EXTENDED_STEP_METERS

    fare = BASE_FARE_TIERS[0][1]
    for threshold, price in BASE_FARE_TIERS:
        if meters >= threshold:
            fare = price
    return fare


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Uses roughly 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: travel distance in meters.
        transfer_count: number of transfers on the route.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
