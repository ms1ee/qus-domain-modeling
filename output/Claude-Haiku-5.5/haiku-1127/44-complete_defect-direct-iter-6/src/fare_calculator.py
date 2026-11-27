"""Beijing Subway fare calculation.

Fare structure (distance in kilometers, rounded up):
    0 - 6 km    : 3 yuan
    6 - 12 km   : 4 yuan
    12 - 22 km  : 5 yuan
    22 - 32 km  : 6 yuan
    > 32 km     : 6 yuan + 1 yuan for every further 20 km (or part thereof)
"""

import math
from typing import List, Tuple

# (upper bound in km inclusive, fare in yuan) for the progressive tiers.
FARE_TIERS: List[Tuple[int, int]] = [(6, 3), (12, 4), (22, 5), (32, 6)]
EXTENSION_START_KM = 32
EXTENSION_STEP_KM = 20
EXTENSION_FARE_INCREMENT = 1

AVERAGE_SPEED_KMH = 35.0  # average operating speed used for time estimates
TRANSFER_TIME_MIN = 4.0   # average time cost of one line transfer in minutes


def _validate_distance(distance: float) -> None:
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("distance must be finite")
    if distance < 0:
        raise ValueError("distance must be non-negative")


def Sum_money(distance: int) -> int:
    """Return the subway fare in yuan for a travelled distance in meters.

    Fractional kilometers are rounded up (ceiling) before tier lookup, so any
    distance beyond a tier boundary falls into the higher tier.

    Args:
        distance: travelled distance in meters.

    Returns:
        Fare in yuan (integer).

    Raises:
        TypeError: if distance is not numeric.
        ValueError: if distance is negative or not finite.
    """
    _validate_distance(distance)
    if distance == 0:
        return 0

    km = math.ceil(distance / 1000)
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    extra_steps = math.ceil((km - EXTENSION_START_KM) / EXTENSION_STEP_KM)
    return FARE_TIERS[-1][1] + extra_steps * EXTENSION_FARE_INCREMENT


def calculate_estimated_time(distance: int, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line transfers.

    Returns:
        Estimated time in minutes, rounded to two decimals.

    Raises:
        TypeError / ValueError: on invalid inputs.
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")

    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = travel_minutes + transfer_count * TRANSFER_TIME_MIN
    return round(total, 2)
