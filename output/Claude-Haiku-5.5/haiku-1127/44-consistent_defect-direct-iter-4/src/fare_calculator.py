"""Fare calculation for the Beijing Subway.

Fare structure (distances in meters, intervals are left-closed, right-open,
so a boundary value enters the next higher tier):
    [0, 6000)          -> 3 yuan
    [6000, 12000)      -> 4 yuan
    [12000, 22000)     -> 5 yuan
    [22000, 32000)     -> 6 yuan
    [32000, 52000)     -> 7 yuan   (extended tier)
    [52000, 72000)     -> 8 yuan
    ...                   +1 yuan for every additional 20 km beyond 32 km

Fractional distances are rounded up to the next whole meter before lookup.
"""

import math

# (lower bound in meters, fare in yuan), sorted ascending.
BASIC_FARE_TIERS = (
    (0, 3),
    (6000, 4),
    (12000, 5),
    (22000, 6),
)

EXTENDED_START_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_METERS = 20000


def Sum_money(distance):
    """Compute the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float). Fractional
            values are rounded up.

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If distance is not a finite non-negative number.
    """
    if distance is None:
        raise ValueError("distance must not be None")
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"distance must be a number, got {distance!r}") from exc
    if math.isnan(value) or math.isinf(value) or value < 0:
        raise ValueError(f"distance must be a finite non-negative number, got {distance!r}")

    meters = math.ceil(value)

    if meters >= EXTENDED_START_METERS:
        extra_steps = (meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS
        return EXTENDED_BASE_FARE + extra_steps

    fare = BASIC_FARE_TIERS[0][1]
    for lower_bound, tier_fare in BASIC_FARE_TIERS:
        if meters >= lower_bound:
            fare = tier_fare
    return fare


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.

    Raises:
        ValueError: If distance or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / 1000.0) * 1.5 + transfer_count * 5.0
