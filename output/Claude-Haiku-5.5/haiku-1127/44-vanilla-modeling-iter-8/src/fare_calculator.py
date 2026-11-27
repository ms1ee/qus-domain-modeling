"""Fare calculation based on the Beijing Subway fare structure.

Fare tiers (left-closed, right-open intervals, distances in meters internally):
    0 - 6 km      : 3 yuan
    6 - 12 km     : 4 yuan
    12 - 22 km    : 5 yuan
    22 - 32 km    : 6 yuan
    >= 32 km      : 7 yuan, plus 1 yuan for every additional 20 km
                    (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)
Fractional meters are rounded up (ceiling) before the tier lookup.
"""

import math
from dataclasses import dataclass

from data_loader import DATA_FILE_PATH  # noqa: F401  (re-exported for convenience)

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


@dataclass(frozen=True)
class FareTier:
    """One tier of the fare structure.

    Attributes:
        tierName: Human readable tier name.
        minDistanceKm: Inclusive lower bound in kilometers.
        maxDistanceKm: Exclusive upper bound in kilometers (inf for the extended tier).
        fareYuan: Fare in yuan for the tier (base fare for the extended tier).
        extensionStepKm: Length of each extension step; 0 for fixed tiers.
    """

    tierName: str
    minDistanceKm: float
    maxDistanceKm: float
    fareYuan: int
    extensionStepKm: float = 0.0


FARE_TIERS = (
    FareTier("Basic", 0.0, 6.0, 3, 0.0),
    FareTier("Progressive-1", 6.0, 12.0, 4, 0.0),
    FareTier("Progressive-2", 12.0, 22.0, 5, 0.0),
    FareTier("Progressive-3", 22.0, 32.0, 6, 0.0),
    FareTier("Extended", 32.0, math.inf, 7, 20.0),
)


def Sum_money(distance):
    """Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters (int or float).

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is not a finite, non-negative number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number of meters, got %r" % (distance,))
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError("Distance must be a finite non-negative number, got %r" % (distance,))

    # Ceiling rounding for fractional distances.
    meters = math.ceil(distance)

    # Fixed tiers: a boundary value belongs to the next (higher) tier.
    for tier in FARE_TIERS[:-1]:
        if meters < int(round(tier.maxDistanceKm * 1000)):
            return tier.fareYuan

    # Extended tier (>= 32 km).
    extended = FARE_TIERS[-1]
    start_m = int(round(extended.minDistanceKm * 1000))
    step_m = int(round(extended.extensionStepKm * 1000))
    return extended.fareYuan + (meters - start_m) // step_m


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.
    """
    if distance < 0:
        raise ValueError("Distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
