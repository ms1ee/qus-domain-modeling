"""Fare calculation for the Beijing Subway fare structure.

Fare tiers:
  * Basic tier:       0-6 km       -> 3 yuan
  * Progressive tier: 6-12 km      -> 4 yuan
                      12-22 km     -> 5 yuan
                      22-32 km     -> 6 yuan
  * Extended tier:    >= 32 km     -> 7 yuan, +1 yuan for every further 20 km
"""

import math

# (min_distance_m, max_distance_m, fare_yuan); a distance d belongs to the
# tier where min <= d < max.
BASE_FARE_TIERS = (
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
)
EXTENDED_START_M = 32000
EXTENDED_BASE_YUAN = 7
EXTENDED_STEP_M = 20000

AVERAGE_SPEED_KMH = 35.0        # average in-service speed used for time estimates
TRANSFER_TIME_MIN = 5.0         # minutes per transfer (walking and waiting)
BOARDING_TIME_MIN = 3.0         # fixed boarding/alighting overhead in minutes


def _validate_distance(distance):
    """Validate a distance in meters and return it as float."""
    if isinstance(distance, bool):
        raise ValueError("distance must be a number")
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"distance must be a number, got {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise ValueError("distance must be a finite number")
    if value < 0:
        raise ValueError("distance must not be negative")
    return value


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Travelled distance in meters (fractional values allowed).

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is negative or not a number.
    """
    value = _validate_distance(distance)
    for min_m, max_m, fare in BASE_FARE_TIERS:
        if value < max_m:
            return fare
    # Extended tier: fare increases by 1 yuan per started 20 km block
    # beyond 32 km.
    return EXTENDED_BASE_YUAN + int((value - EXTENDED_START_M) // EXTENDED_STEP_M)


def get_fare_tier_name(distance):
    """Return the name of the fare tier applicable to a distance in meters."""
    value = _validate_distance(distance)
    if value < 6000:
        return "Basic"
    if value < EXTENDED_START_M:
        return "Progressive"
    return "Extended"


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        float: Estimated travel time in minutes.
    """
    value = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise ValueError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    in_motion = (value / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return in_motion + transfer_count * TRANSFER_TIME_MIN + BOARDING_TIME_MIN
