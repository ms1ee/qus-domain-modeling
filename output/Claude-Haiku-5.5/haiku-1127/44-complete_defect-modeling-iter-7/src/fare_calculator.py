"""Beijing Subway fare calculation and travel time estimation."""

from __future__ import annotations

import math

# Fare tiers as (upper bound in km, inclusive; fare in yuan).
# 0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan.
FARE_TIERS: tuple[tuple[int, int], ...] = ((6, 3), (12, 4), (22, 5), (32, 6))
# Beyond 32 km, one extra yuan for every further 20 km (or part thereof).
EXTENSION_START_KM = 32
EXTENSION_STEP_KM = 20
EXTENSION_INCREMENT_YUAN = 1

# Travel time model parameters.
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def _round_up_to_km(distance_m: float) -> int:
    """Round a distance in meters up to whole kilometers (fractional km round up)."""
    meters = math.ceil(distance_m)
    return -(-meters // 1000)


def Sum_money(distance: float) -> int:
    """Calculate the subway fare for a distance.

    Args:
        distance: travelled distance in meters.

    Returns:
        The fare in yuan (0 for a zero-length trip).

    Raises:
        ValueError: if the distance is negative.
    """
    if distance < 0:
        raise ValueError("distance cannot be negative")
    if distance == 0:
        return 0
    km = _round_up_to_km(distance)
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare
    extra_km = km - EXTENSION_START_KM
    steps = -(-extra_km // EXTENSION_STEP_KM)
    return FARE_TIERS[-1][1] + steps * EXTENSION_INCREMENT_YUAN


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line changes.

    Returns:
        Estimated travel time in minutes.

    Raises:
        ValueError: if inputs are negative.
    """
    if distance < 0:
        raise ValueError("distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("transfer count cannot be negative")
    riding = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return float(riding + transfer_count * TRANSFER_TIME_MINUTES)
