"""
Fare and travel-time calculation for Beijing Subway.

Fare structure (distance in meters, intervals are left-closed, right-open):
  [0, 6 km)        -> 3 yuan
  [6 km, 12 km)    -> 4 yuan
  [12 km, 22 km)   -> 5 yuan
  [22 km, 32 km)   -> 6 yuan
  [32 km, ...)     -> 7 yuan, plus 1 yuan for every additional 20 km
                      (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Fractional distances are rounded up to the next whole meter before the
tier lookup, so the boundary values themselves enter the next tier.
"""

import math

# (lower bound inclusive, upper bound exclusive, fare in yuan) in meters.
FARE_TIERS = (
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
)
EXTENSION_START_METERS = 32000
EXTENSION_BASE_FARE = 7
EXTENSION_STEP_METERS = 20000

# Travel-time model.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance in meters.

    Args:
        distance: Distance in meters (int or float, fractional values are rounded up).

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is negative or not a finite number.
    """
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid distance: {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Distance must be finite, got {distance!r}")
    if value < 0:
        raise ValueError(f"Distance must be non-negative, got {distance!r}")

    meters = math.ceil(value)
    for lower, upper, fare in FARE_TIERS:
        if lower <= meters < upper:
            return fare
    # Extended tier: 7 yuan at 32 km, +1 yuan every 20 km.
    return EXTENSION_BASE_FARE + (meters - EXTENSION_START_METERS) // EXTENSION_STEP_METERS


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: About 1.5 minutes per kilometre plus about 5 minutes per transfer.
    """
    if distance < 0:
        raise ValueError("Distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
