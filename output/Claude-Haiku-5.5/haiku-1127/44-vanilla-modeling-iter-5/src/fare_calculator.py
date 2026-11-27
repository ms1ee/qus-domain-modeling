"""Beijing Subway fare calculation.

Fare tiers (left-closed, right-open intervals):
    [0, 6) km      -> 3 yuan
    [6, 12) km     -> 4 yuan
    [12, 22) km    -> 5 yuan
    [22, 32) km    -> 6 yuan
    [32, ...) km   -> 7 yuan, +1 yuan for every further 20 km
Fractional meters are rounded up (ceiling) before tier lookup.
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
        min_distance_km: inclusive lower bound in kilometers.
        max_distance_km: exclusive upper bound, or None for the open-ended tier.
        fare_yuan: fare charged at the lower bound of the tier.
        extension_step_km: for the extended tier, km per additional yuan.
    """

    min_distance_km: float
    max_distance_km: Optional[float]
    fare_yuan: int
    extension_step_km: Optional[float] = None


FARE_TIERS = (
    FareTier(0.0, 6.0, 3),
    FareTier(6.0, 12.0, 4),
    FareTier(12.0, 22.0, 5),
    FareTier(22.0, 32.0, 6),
    FareTier(32.0, None, 7, 20.0),
)


def _km_to_meters(km):
    """Convert kilometers to integer meters without float drift."""
    return int(round(km * 1000))


def _normalize_distance(distance):
    """Validate a distance in meters and round it up to a whole meter.

    Raises:
        ValueError: If the value is not a finite non-negative number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("distance must be a number of meters")
    value = float(distance)
    if not math.isfinite(value):
        raise ValueError("distance must be finite")
    if value < 0:
        raise ValueError("distance must not be negative")
    return int(math.ceil(value))


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: travelled distance in meters.

    Returns:
        int: fare in yuan.

    Raises:
        ValueError: If the distance is invalid.
    """
    meters = _normalize_distance(distance)
    for tier in FARE_TIERS:
        min_m = _km_to_meters(tier.min_distance_km)
        if tier.max_distance_km is None:
            step_m = _km_to_meters(tier.extension_step_km)
            return tier.fare_yuan + (meters - min_m) // step_m
        if meters < _km_to_meters(tier.max_distance_km):
            return tier.fare_yuan
    raise ValueError("no fare tier matches the distance")  # pragma: no cover


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of transfers.

    Returns:
        float: estimated minutes (about 1.5 min per km plus 5 min per transfer).

    Raises:
        ValueError: If inputs are invalid.
    """
    meters = _normalize_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise ValueError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    return (meters / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
