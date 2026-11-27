"""Beijing Subway fare calculation based on travelled distance."""

import math

# Distance tiers: (upper bound in meters inclusive, fare in yuan).
FARE_TIERS = (
    (6000, 3),    # 0-6 km: 3 yuan
    (12000, 4),   # 6-12 km: 4 yuan
    (22000, 5),   # 12-22 km: 5 yuan
    (32000, 6),   # 22-32 km: 6 yuan
)
EXTENSION_START_M = 32000     # beyond this distance the extended rule applies
EXTENSION_STEP_M = 20000      # every additional 20 km ...
EXTENSION_STEP_YUAN = 1       # ... adds 1 yuan

AVERAGE_SPEED_KMH = 35.0      # assumed average operating speed
TRANSFER_TIME_MIN = 4.0       # assumed time per transfer in minutes


def _ceil_distance(distance):
    """Validate a distance in meters and round fractional values up to whole meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    return int(math.ceil(distance))


def Sum_money(distance):
    """Return the subway fare in yuan for a trip of `distance` meters.

    Rules:
        0-6 km: 3 yuan; 6-12 km: 4 yuan; 12-22 km: 5 yuan; 22-32 km: 6 yuan.
        Beyond 32 km: 1 extra yuan for every 20 km (or fraction thereof).
    Fractional distances are rounded up to the next whole meter before lookup.

    Args:
        distance: Travelled distance in meters.

    Returns:
        Fare as an integer number of yuan.
    """
    meters = _ceil_distance(distance)
    for upper_bound, fare in FARE_TIERS:
        if meters <= upper_bound:
            return fare
    extra = meters - EXTENSION_START_M
    steps = -(-extra // EXTENSION_STEP_M)  # ceiling division
    return FARE_TIERS[-1][1] + steps * EXTENSION_STEP_YUAN


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line transfers.

    Returns:
        Estimated travel time in minutes, rounded to one decimal place.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    transfer_minutes = transfer_count * TRANSFER_TIME_MIN
    return round(travel_minutes + transfer_minutes, 1)
