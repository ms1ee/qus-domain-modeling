"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distance intervals are left-closed, right-open):
    [0, 6 km)        -> 3 yuan
    [6, 12 km)       -> 4 yuan
    [12, 22 km)      -> 5 yuan
    [22, 32 km)      -> 6 yuan
    [32 km, ...)     -> 7 yuan, plus 1 yuan for every further 20 km
"""

import math

# (exclusive upper bound in meters, fare in yuan) for the basic/progressive tiers.
FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
EXTENSION_BASE_METERS = 32000
EXTENSION_STEP_METERS = 20000
EXTENSION_BASE_FARE = 7

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance) -> int:
    """Return the fare in yuan for a travel distance given in meters.

    Fractional distances are rounded up to the next whole meter before the
    tier lookup (ceiling rounding).

    Raises:
        TypeError: if ``distance`` is not a real number.
        ValueError: if ``distance`` is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"distance must be a number of meters, got {type(distance).__name__}")
    if not math.isfinite(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)
    for upper_bound, fare in FARE_TIERS:
        if meters < upper_bound:
            return fare
    # Extended tier: 7 yuan at 32 km, +1 yuan per 20 km thereafter.
    return EXTENSION_BASE_FARE + (meters - EXTENSION_BASE_METERS) // EXTENSION_STEP_METERS


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated travel time in minutes.

    Args:
        distance: travel distance in meters.
        transfer_count: number of transfers.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.
    """
    if distance < 0:
        raise ValueError("distance must not be negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
