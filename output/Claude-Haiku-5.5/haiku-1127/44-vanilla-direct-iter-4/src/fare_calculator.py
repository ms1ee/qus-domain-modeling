"""Beijing Subway fare calculation.

Fare structure (distance in meters, left-closed right-open intervals):
    [0, 6 km)        -> 3 yuan
    [6 km, 12 km)    -> 4 yuan
    [12 km, 22 km)   -> 5 yuan
    [22 km, 32 km)   -> 6 yuan
    [32 km, ...)     -> 7 yuan, plus 1 yuan for every further 20 km
                        (32-52 km: 7, 52-72 km: 8, ...)
Fractional distances are rounded up to the next whole meter before lookup.
"""

import math

BASE_FARE = 3
# (lower bound in meters, fare in yuan) for the progressive tiers.
PROGRESSIVE_TIERS = (
    (6000, 4),
    (12000, 5),
    (22000, 6),
)
EXTENDED_START_M = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_M = 20000


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Travelled distance in meters. Fractional values are rounded up.

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If ``distance`` is not a real number.
        ValueError: If ``distance`` is negative or not finite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance cannot be negative")

    meters = math.ceil(distance)
    if meters < PROGRESSIVE_TIERS[0][0]:
        return BASE_FARE
    fare = BASE_FARE
    for lower_bound, tier_fare in PROGRESSIVE_TIERS:
        if meters >= lower_bound:
            fare = tier_fare
    if meters < EXTENDED_START_M:
        return fare
    extra_steps = (meters - EXTENDED_START_M) // EXTENDED_STEP_M
    return EXTENDED_BASE_FARE + int(extra_steps)


def format_fare(fare):
    """Format a fare for display, e.g. ``"Fare: 4 yuan"``."""
    return f"Fare: {fare} yuan"


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.

    Raises:
        ValueError: If an argument is negative.
    """
    if distance < 0:
        raise ValueError("distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("transfer_count cannot be negative")
    distance_km = distance / 1000.0
    return distance_km * 1.5 + transfer_count * 5.0
