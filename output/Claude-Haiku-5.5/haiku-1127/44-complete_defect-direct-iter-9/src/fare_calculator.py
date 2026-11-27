"""Beijing Subway fare and travel time calculation.

Fare structure:
    0-6 km: 3 yuan; 6-12 km: 4 yuan; 12-22 km: 5 yuan; 22-32 km: 6 yuan.
    Beyond 32 km: +1 yuan for every additional (started) 20 km.
Distances are rounded up to the next whole meter before tier lookup.
"""

import math

# (upper bound in meters inclusive, fare in yuan)
FARE_TIERS = ((6000, 3), (12000, 4), (22000, 5), (32000, 6))
EXTENSION_START_M = 32000
EXTENSION_STEP_M = 20000
EXTENSION_STEP_FARE = 1

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MIN = 5.0


class FareError(ValueError):
    """Raised when fare or time calculation receives invalid input."""


def _validate_distance(distance):
    """Validate a distance in meters and return it.

    Raises:
        FareError: If the distance is not a finite non-negative number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareError(f"distance must be a number, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise FareError("distance must be finite")
    if distance < 0:
        raise FareError("distance must be non-negative")
    return distance


def Sum_money(distance):
    """Compute the subway fare for a distance.

    Args:
        distance: Travelled distance in meters. Fractional values are rounded up.

    Returns:
        int: Fare in yuan.

    Raises:
        FareError: If the distance is invalid.
    """
    value = _validate_distance(distance)
    meters = math.ceil(value)
    for upper, fare in FARE_TIERS:
        if meters <= upper:
            return fare
    extra = meters - EXTENSION_START_M
    steps = math.ceil(extra / EXTENSION_STEP_M)
    return FARE_TIERS[-1][1] + steps * EXTENSION_STEP_FARE


def fare_table():
    """Return the fare tiers as a list of (description, fare in yuan) tuples."""
    rows = []
    previous = 0
    for upper, fare in FARE_TIERS:
        rows.append((f"{previous / 1000:g}-{upper / 1000:g} km", fare))
        previous = upper
    rows.append((f"over {EXTENSION_START_M / 1000:g} km (+{EXTENSION_STEP_FARE} yuan per "
                 f"{EXTENSION_STEP_M / 1000:g} km)", FARE_TIERS[-1][1]))
    return rows


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.

    Raises:
        FareError: If the inputs are invalid.
    """
    value = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise FareError("transfer_count must be a non-negative integer")
    travel_minutes = (value / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return float(travel_minutes + transfer_count * TRANSFER_TIME_MIN)
