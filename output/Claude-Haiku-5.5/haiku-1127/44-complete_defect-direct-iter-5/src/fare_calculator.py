"""Fare calculation for the Beijing Subway.

Fare structure:
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    over 32 km: 6 yuan + 1 yuan for every further (or partial) 20 km

Distances are measured in meters and rounded up to whole kilometers before
the tier lookup, so fractional distances are charged at the next kilometer.
"""

from __future__ import annotations

import math
from typing import List, Tuple

# Mapping of distance tiers: (upper bound in km inclusive, fare in yuan).
FARE_TIERS: List[Tuple[int, int]] = [(6, 3), (12, 4), (22, 5), (32, 6)]
EXTENSION_STEP_KM: int = 20
EXTENSION_STEP_FARE: int = 1

# Parameters for the rough travel time estimate.
AVERAGE_SPEED_KMH: float = 35.0
TRANSFER_TIME_MINUTES: float = 5.0


def _ceil_km(distance_m: float) -> int:
    """Round a distance in meters up to whole kilometers."""
    if distance_m < 0:
        raise ValueError("Distance cannot be negative")
    return math.ceil(distance_m / 1000.0)


def Sum_money(distance: float) -> int:
    """Calculate the subway fare in yuan for a distance given in meters.

    Args:
        distance: Travelled distance in meters.

    Returns:
        The fare in yuan as an integer.

    Raises:
        ValueError: If the distance is negative.
    """
    km = _ceil_km(distance)
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    last_upper_km, last_fare = FARE_TIERS[-1]
    extra_km = km - last_upper_km
    steps = math.ceil(extra_km / EXTENSION_STEP_KM)
    return last_fare + steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated travel time in minutes.

    Raises:
        ValueError: If distance is negative or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return travel_minutes + transfer_count * TRANSFER_TIME_MINUTES
