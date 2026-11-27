"""Beijing Subway fare calculation.

Fare structure (distance in meters, intervals are left-closed, right-open):
    [0, 6000)             -> 3 yuan
    [6000, 12000)         -> 4 yuan
    [12000, 22000)        -> 5 yuan
    [22000, 32000)        -> 6 yuan
    [32000, ...)          -> 7 yuan, plus 1 yuan per additional 20 km
                             (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Fractional distances are rounded up to the next whole meter before the
tier lookup.
"""

import math

# (exclusive upper bound in meters, fare in yuan) for the basic/progressive tiers.
FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
EXTENDED_START_M = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_M = 20000

# Estimated travel time parameters.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def _normalize_distance(distance):
    """Validate a distance in meters and round it up to a whole meter."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")
    return math.ceil(distance)


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Travelled distance in meters. Fractional values are rounded
            up to the next whole meter.

    Returns:
        int: The fare in yuan.

    Raises:
        TypeError: If ``distance`` is not a number.
        ValueError: If ``distance`` is negative, NaN, or infinite.
    """
    meters = _normalize_distance(distance)
    for upper_bound, fare in FARE_TIERS:
        if meters < upper_bound:
            return fare
    extra_steps = (meters - EXTENDED_START_M) // EXTENDED_STEP_M
    return EXTENDED_BASE_FARE + int(extra_steps)


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Uses approximately 1.5 minutes per kilometer plus approximately 5 minutes
    per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.

    Raises:
        TypeError: If the arguments are not numbers.
        ValueError: If the arguments are negative or not finite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError("distance must be a finite, non-negative number")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    distance_km = distance / 1000.0
    return float(distance_km * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
