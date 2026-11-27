"""Beijing Subway fare calculation and travel-time estimation.

Fare structure (distance in meters, left-closed / right-open intervals):
    [0, 6 km)        -> 3 yuan
    [6 km, 12 km)    -> 4 yuan
    [12 km, 22 km)   -> 5 yuan
    [22 km, 32 km)   -> 6 yuan
    [32 km, ...)     -> 7 yuan, +1 yuan for every further 20 km
                        (32-52 km: 7, 52-72 km: 8, ...)

Fractional distances are rounded up (ceiling) to whole meters before the
tier lookup, so a boundary value always falls into the next higher tier.
"""
from __future__ import annotations

import math

BASE_FARE_YUAN = 3
EXTENDED_TIER_START_M = 32000
EXTENDED_STEP_M = 20000

# Estimated-time model
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance: float) -> int:
    """Return the subway fare in yuan for a travel distance in meters.

    Args:
        distance: travel distance in meters (may be fractional; rounded up).

    Returns:
        Fare in whole yuan.

    Raises:
        ValueError: if the distance is negative, NaN, infinite or not numeric.
    """
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Distance must be numeric, got {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Distance must be finite, got {distance!r}")
    if value < 0:
        raise ValueError(f"Distance must be non-negative, got {distance!r}")

    meters = math.ceil(value)  # ceiling rounding of fractional distances

    if meters < 6000:
        return 3
    if meters < 12000:
        return 4
    if meters < 22000:
        return 5
    if meters < EXTENDED_TIER_START_M:
        return 6
    # Extended tier: 7 yuan at 32 km, plus 1 yuan per additional 20 km.
    return 7 + (meters - EXTENDED_TIER_START_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Model: about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: travel distance in meters.
        transfer_count: number of line transfers.

    Returns:
        Estimated travel time in minutes, rounded to two decimals.

    Raises:
        ValueError: if distance or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError(f"Distance must be non-negative, got {distance}")
    if transfer_count < 0:
        raise ValueError(f"Transfer count must be non-negative, got {transfer_count}")
    minutes = (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
    return round(minutes, 2)
