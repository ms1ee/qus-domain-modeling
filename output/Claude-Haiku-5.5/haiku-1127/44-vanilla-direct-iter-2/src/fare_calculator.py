"""Fare and travel-time calculations for the Beijing Subway.

Fare structure (distance in meters, intervals are left-closed, right-open):
    0      <= d < 6000        : 3 yuan
    6000   <= d < 12000       : 4 yuan
    12000  <= d < 22000       : 5 yuan
    22000  <= d < 32000       : 6 yuan
    d      >= 32000           : 7 yuan, plus 1 yuan for every further 20 km
                                (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Fractional distances are rounded up (ceiling) to whole meters before the
tier lookup, so a boundary value always enters the next higher tier.
"""

import math

# (lower bound in meters, fare in yuan) for the basic and progressive tiers.
FARE_TIERS = (
    (0, 3),
    (6000, 4),
    (12000, 5),
    (22000, 6),
)

# Extended tier: starts at 32 km with 7 yuan, +1 yuan per 20 km.
EXTENDED_TIER_START_M = 32000
EXTENDED_TIER_BASE_FARE = 7
EXTENDED_TIER_STEP_M = 20000

# Estimated travel time parameters (used for summaries and comprehensive routing).
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _validate_distance(distance):
    """Ensure a distance value is a finite, non-negative real number."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number of meters, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the subway fare (integer yuan) for a travelled distance in meters.

    Fractional meters are rounded up, and boundary values are charged at the
    next higher tier (left-closed, right-open rule).
    """
    _validate_distance(distance)
    meters = math.ceil(distance)

    if meters >= EXTENDED_TIER_START_M:
        extra_steps = (meters - EXTENDED_TIER_START_M) // EXTENDED_TIER_STEP_M
        return EXTENDED_TIER_BASE_FARE + extra_steps

    fare = FARE_TIERS[0][1]
    for lower_bound, tier_fare in FARE_TIERS:
        if meters >= lower_bound:
            fare = tier_fare
    return fare


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometre plus about 5 minutes per transfer.
    ``distance`` is in meters.
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count cannot be negative")
    riding_minutes = (distance / 1000.0) * MINUTES_PER_KM
    transfer_minutes = transfer_count * MINUTES_PER_TRANSFER
    return float(riding_minutes + transfer_minutes)
