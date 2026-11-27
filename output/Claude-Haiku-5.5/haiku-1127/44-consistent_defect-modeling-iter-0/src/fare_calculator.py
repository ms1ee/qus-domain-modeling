"""Fare and travel-time calculation based on the Beijing Subway fare structure."""

import math
from dataclasses import dataclass

# Travel-time model: about 1.5 minutes per kilometre plus 5 minutes per transfer.
SPEED_MINUTES_PER_KM = 1.5
TRANSFER_TIME_MINUTES = 5.0

# Extended tier: beyond 32 km, +1 yuan for every additional 20 km (ceiling).
EXTENSION_BASE_METERS = 32000.0
EXTENSION_STEP_METERS = 20000.0


@dataclass(frozen=True)
class FareTier:
    """A distance band with a flat fare.

    Attributes:
        min_distance_km: lower bound of the band in kilometres.
        max_distance_km: upper bound of the band in kilometres.
        fare_yuan: flat fare charged inside the band.
        extension_step_km: step length for extended tiers (0 for flat tiers).
        upper_inclusive: whether the upper bound belongs to this band.
    """

    min_distance_km: float
    max_distance_km: float
    fare_yuan: int
    extension_step_km: float = 0.0
    upper_inclusive: bool = True


# Flat fare tiers, checked in order. Each tier's upper bound is the next tier's
# lower bound; boundary values follow the PRD examples
# (6 km -> 3 yuan, 12 km -> 4 yuan, 22 km -> 6 yuan, 32 km -> 6 yuan).
FARE_TIERS = (
    FareTier(0.0, 6.0, 3, 0.0, True),
    FareTier(6.0, 12.0, 4, 0.0, True),
    FareTier(12.0, 22.0, 5, 0.0, False),
    FareTier(22.0, 32.0, 6, 0.0, True),
)


def Sum_money(distance):
    """Return the fare in yuan for a travel distance given in meters.

    Rules:
        * distance <= 6000 m                 -> 3 yuan
        * 6000 m < distance <= 12000 m        -> 4 yuan
        * 12000 m <= distance < 22000 m       -> 5 yuan
        * 22000 m <= distance <= 32000 m      -> 6 yuan
        * distance > 32000 m                  -> 6 + ceil((distance - 32000) / 20000)

    Fractional distances are handled by ceiling rounding of the extension
    steps, so any distance strictly beyond 32 km is charged for a full step.

    Raises:
        ValueError: if the distance is not a finite non-negative number.
    """
    try:
        meters = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid distance: {distance!r}") from exc
    if math.isnan(meters) or math.isinf(meters) or meters < 0:
        raise ValueError(f"distance must be a finite non-negative number: {distance!r}")

    km = meters / 1000.0
    for tier in FARE_TIERS:
        within = km <= tier.max_distance_km if tier.upper_inclusive else km < tier.max_distance_km
        if within:
            return int(tier.fare_yuan)

    base_fare = FARE_TIERS[-1].fare_yuan
    extra_steps = math.ceil((meters - EXTENSION_BASE_METERS) / EXTENSION_STEP_METERS)
    return int(base_fare + extra_steps)


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfer count."""
    meters = max(0.0, float(distance))
    transfers = max(0, int(transfer_count))
    return (meters / 1000.0) * SPEED_MINUTES_PER_KM + transfers * TRANSFER_TIME_MINUTES
