"""Fare and travel-time calculation for Beijing Subway trips.

Fare structure (distance in meters, boundaries inclusive on the lower side):
    0      <= d < 6000        -> 3 yuan   (basic tier)
    6000   <= d < 12000       -> 4 yuan   (progressive tier)
    12000  <= d < 22000       -> 5 yuan   (progressive tier)
    22000  <= d < 32000       -> 6 yuan   (progressive tier)
    d >= 32000                -> 7 yuan, plus 1 yuan for every further
                                 20 km (extended tier)
Fractional distances are rounded half-up to whole meters before lookup.
"""

import math

from errors import FareCalculationError

# (lower bound in meters, fare in yuan), ordered by ascending lower bound.
BASIC_TIER_THRESHOLDS = ((0, 3), (6000, 4), (12000, 5), (22000, 6))
EXTENDED_TIER_START_M = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_M = 20000

# Travel-time model parameters.
AVERAGE_SPEED_KMH = 35.0     # average commercial speed including station stops
BOARDING_MINUTES = 2.0       # fixed time to board and start the trip
TRANSFER_MINUTES = 4.0       # average time lost per line transfer


def _normalise_distance(distance):
    """Validate a distance in meters and round it to whole meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError(f"distance must be a number, got {distance!r}")
    value = float(distance)
    if math.isnan(value) or math.isinf(value):
        raise FareCalculationError("distance must be a finite number")
    if value < 0:
        raise FareCalculationError("distance must not be negative")
    return int(math.floor(value + 0.5))


def Sum_money(distance):
    """Calculate the subway fare in yuan for a trip of ``distance`` meters.

    Args:
        distance: Travelled distance in meters (int or float).

    Returns:
        int: Fare in yuan.

    Raises:
        FareCalculationError: If the distance is invalid.
    """
    meters = _normalise_distance(distance)
    if meters >= EXTENDED_TIER_START_M:
        return EXTENDED_BASE_FARE + (meters - EXTENDED_TIER_START_M) // EXTENDED_STEP_M
    fare = BASIC_TIER_THRESHOLDS[0][1]
    for lower_bound, tier_fare in BASIC_TIER_THRESHOLDS:
        if meters >= lower_bound:
            fare = tier_fare
    return fare


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    The estimate combines riding time at an average speed, a fixed boarding
    allowance, and a penalty for every line transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line transfers (non-negative int).

    Returns:
        float: Estimated minutes, rounded to one decimal place.

    Raises:
        FareCalculationError: If an argument is invalid.
    """
    meters = _normalise_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise FareCalculationError("transfer count must be an integer")
    if transfer_count < 0:
        raise FareCalculationError("transfer count must not be negative")
    riding = meters / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    boarding = BOARDING_MINUTES if meters > 0 else 0.0
    minutes = riding + boarding + transfer_count * TRANSFER_MINUTES
    return round(minutes, 1)
