"""
Fare and travel-time calculation for the Beijing Subway.

Fare structure (distance rounded up to whole kilometers):
  * 0-6 km    : 3 yuan
  * 6-12 km   : 4 yuan
  * 12-22 km  : 5 yuan
  * 22-32 km  : 6 yuan
  * > 32 km   : 6 yuan + 1 yuan for every further (or part of) 20 km
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FareTier:
    """A fare band: distances up to ``max_distance_km`` (inclusive) cost ``fare_yuan``."""

    min_distance_km: float
    max_distance_km: float
    fare_yuan: int


# Base fare tiers (ceiling-rounded kilometers are matched against these bounds).
FARE_TIERS = (
    FareTier(0.0, 6.0, 3),
    FareTier(6.0, 12.0, 4),
    FareTier(12.0, 22.0, 5),
    FareTier(22.0, 32.0, 6),
)

# Extended fare: beyond the last tier's upper bound.
EXTENSION_START_KM = 32.0
EXTENSION_STEP_KM = 20.0
EXTENSION_STEP_FARE = 1

# Average operating speed used for time estimation (km/h).
AVERAGE_SPEED_KMH = 35.0
# Time cost of each transfer (minutes), covering walking and waiting.
TRANSFER_TIME_MINUTES = 5.0


def _validate_distance(distance):
    """Ensure the distance is a non-negative real number."""
    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance cannot be negative")


def ceil_kilometers(distance):
    """
    Round a distance in meters up to whole kilometers.

    Any fraction of a kilometer counts as a full kilometer, which implements
    the ceiling rounding required by the fare structure.
    """
    _validate_distance(distance)
    return int(math.ceil(distance / 1000.0))


def Sum_money(distance):
    """
    Compute the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters.

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError / ValueError: If the distance is not a valid non-negative number.
    """
    kilometers = ceil_kilometers(distance)

    for tier in FARE_TIERS:
        if kilometers <= tier.max_distance_km:
            return tier.fare_yuan

    extra_km = kilometers - EXTENSION_START_KM
    steps = int(math.ceil(extra_km / EXTENSION_STEP_KM))
    return FARE_TIERS[-1].fare_yuan + steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate the travel time of a journey in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the journey.

    Returns:
        float: Estimated travel time in minutes.
    """
    _validate_distance(distance)
    if not isinstance(transfer_count, int) or isinstance(transfer_count, bool) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")

    riding_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    transfer_minutes = transfer_count * TRANSFER_TIME_MINUTES
    return float(riding_minutes + transfer_minutes)
