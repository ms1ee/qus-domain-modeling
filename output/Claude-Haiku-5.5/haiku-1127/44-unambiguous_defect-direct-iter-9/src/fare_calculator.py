"""Beijing Subway fare calculation and journey time estimation.

Fare structure:
* 0-6 km: 3 yuan
* 6-12 km: 4 yuan (boundary 6000 m belongs to this tier)
* 12-22 km: 5 yuan (boundary 12000 m belongs to this tier)
* 22-32 km: 6 yuan (boundary 22000 m belongs to this tier)
* over 32 km: 7 yuan at 32 km, then +1 yuan for every further 20 km
  (any started 20 km block is charged, i.e. the distance is rounded up).
"""

import math
from bisect import bisect_right

#: Lower bounds (meters) of the basic tiers 6 km, 12 km, 22 km and 32 km.
BASIC_FARE_THRESHOLDS_M = (6000, 12000, 22000, 32000)
#: Fares (yuan) for the tiers 0-6, 6-12, 12-22, 22-32 and >32 km.
BASIC_FARES = (3, 4, 5, 6, 7)
EXTENSION_START_M = 32000
EXTENSION_STEP_M = 20000
EXTENSION_STEP_FARE = 1

#: Average train speed used for time estimation (km/h).
TRAIN_SPEED_KMH = 35.0
#: Fixed time for boarding and platform handling (minutes).
BOARDING_MINUTES = 3.0
#: Walking and waiting time added per transfer (minutes).
TRANSFER_MINUTES = 5.0


class FareError(ValueError):
    """Raised when a fare or time cannot be calculated from the given input."""


def _validate_distance(distance):
    """Validate a distance in meters and return it as a float-compatible number."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise FareError("distance must be a finite number")
    if distance < 0:
        raise FareError("distance must not be negative")
    return distance


def Sum_money(distance):
    """Compute the subway fare (yuan) for a travelled distance.

    Args:
        distance: Travelled distance in meters.

    Returns:
        int: The fare in yuan.

    Raises:
        FareError: If the distance is not a valid non-negative number.
    """
    d = _validate_distance(distance)
    if d <= EXTENSION_START_M:
        # bisect_right places boundary values in the higher tier, e.g. 6000 -> 4 yuan.
        return BASIC_FARES[bisect_right(BASIC_FARE_THRESHOLDS_M, d)]
    blocks = math.ceil((d - EXTENSION_START_M) / EXTENSION_STEP_M)
    return BASIC_FARES[-1] + blocks * EXTENSION_STEP_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimate the journey time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        float: Estimated travel time in minutes, rounded to one decimal.

    Raises:
        FareError: If the inputs are invalid.
    """
    d = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise FareError("transfer_count must be a non-negative integer")
    riding_minutes = (d / 1000.0) / TRAIN_SPEED_KMH * 60.0
    total = BOARDING_MINUTES + riding_minutes + transfer_count * TRANSFER_MINUTES
    return round(total, 1)
