"""Fare and travel time calculation for Beijing Subway trips.

Fare structure (distance in kilometers, fractional distances are rounded up):
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    beyond 32 km: +1 yuan for every additional 20 km (or part thereof)
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class FareTier:
    """A distance band of the progressive fare table."""

    min_distance_km: int
    max_distance_km: int
    fare_yuan: int


# Progressive fare tiers, ordered by distance.
FARE_TIERS: Tuple[FareTier, ...] = (
    FareTier(0, 6, 3),
    FareTier(6, 12, 4),
    FareTier(12, 22, 5),
    FareTier(22, 32, 6),
)

# Extended fare settings for trips longer than the last progressive tier.
EXTENSION_THRESHOLD_KM = 32
EXTENSION_BLOCK_KM = 20
EXTENSION_INCREMENT_YUAN = 1

# Parameters for the estimated travel time.
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def ceil_distance_km(distance: float) -> int:
    """Convert a distance in meters to whole kilometers, rounding up.

    Raises:
        ValueError: If the distance is negative.
    """
    if distance < 0:
        raise ValueError(f"Distance must be non-negative, got {distance}")
    return int(math.ceil(distance / 1000.0))


def Sum_money(distance: float) -> int:
    """Calculate the subway fare in yuan for a trip of ``distance`` meters.

    Args:
        distance: Travelled distance in meters.

    Returns:
        The fare in yuan as an integer.

    Raises:
        ValueError: If the distance is negative.
    """
    km = ceil_distance_km(distance)
    for tier in FARE_TIERS:
        if km <= tier.max_distance_km:
            return tier.fare_yuan
    extra_km = km - EXTENSION_THRESHOLD_KM
    blocks = int(math.ceil(extra_km / EXTENSION_BLOCK_KM))
    return FARE_TIERS[-1].fare_yuan + blocks * EXTENSION_INCREMENT_YUAN


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate the travel time in minutes.

    The estimate combines in-vehicle time at an average speed with a fixed
    penalty for every transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated travel time in minutes.

    Raises:
        ValueError: If the distance or transfer count is negative.
    """
    if distance < 0:
        raise ValueError(f"Distance must be non-negative, got {distance}")
    if transfer_count < 0:
        raise ValueError(f"Transfer count must be non-negative, got {transfer_count}")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return travel_minutes + transfer_count * TRANSFER_TIME_MINUTES
