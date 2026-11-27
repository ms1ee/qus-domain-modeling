"""Beijing Subway fare calculation.

Fare structure used (distances in meters):

* 0 - 6 km (exclusive of 6 km):        3 yuan
* 6 km - 12 km (exclusive of 12 km):   4 yuan
* 12 km - 22 km (exclusive of 22 km):  5 yuan
* 22 km - 32 km (inclusive of 32 km):  6 yuan
* Over 32 km: 6 yuan plus 1 yuan for every further 20 km
  (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Boundary values belong to the next (higher) tier, i.e. intervals are
left-closed and right-open, except that the 32 km point itself stays in the
6-yuan band as stated in the requirements. Fractional meters are rounded up.
"""

import math

# (upper bound in meters, exclusive) -> fare in yuan for distances below it.
BASIC_FARE_TIERS = ((6000, 3), (12000, 4), (22000, 5), (32000, 6))
EXTENDED_THRESHOLD_METERS = 32000
EXTENDED_STEP_METERS = 20000
EXTENDED_BASE_FARE = 6


def Sum_money(distance) -> int:
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float, fractional
            meters are rounded up).

    Returns:
        The fare in yuan as an integer.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)
    for upper_bound, fare in BASIC_FARE_TIERS:
        if meters < upper_bound:
            return fare
    if meters <= EXTENDED_THRESHOLD_METERS:
        return EXTENDED_BASE_FARE

    extra_steps = math.ceil((meters - EXTENDED_THRESHOLD_METERS) / EXTENDED_STEP_METERS)
    return EXTENDED_BASE_FARE + extra_steps


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes.

    Uses roughly 1.5 minutes per kilometre plus roughly 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated travel time in minutes.
    """
    kilometers = distance / 1000.0
    return round(kilometers * 1.5 + transfer_count * 5.0, 2)
