"""Beijing Subway fare calculation and travel time estimation.

Fare structure:
    0 - 6 km (exclusive of 6 km)  : 3 yuan
    6 - 12 km                     : 4 yuan
    12 - 22 km                    : 5 yuan
    22 - 32 km                    : 6 yuan
    32 km and above               : 7 yuan, plus 1 yuan for every further 20 km
Fractional meters are rounded up to the next whole meter before tier lookup.
"""

import math

AVERAGE_SPEED_KMH = 35.0    # commercial speed including station dwell time
BOARDING_MINUTES = 3.0      # average waiting and boarding time
TRANSFER_MINUTES = 6.0      # walking and waiting time per line change

_TIER_BOUNDARIES_M = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
_EXTENDED_BASE_M = 32000
_EXTENDED_BASE_FARE = 7
_EXTENDED_STEP_M = 20000


def _validated_meters(distance):
    """Validate a distance in meters and round fractional values up."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance cannot be negative")
    return math.ceil(distance)


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance in meters.

    Boundary values enter the next tier: 6000 m -> 4 yuan, 12000 m -> 5 yuan,
    22000 m -> 6 yuan, 32000 m -> 7 yuan.
    """
    meters = _validated_meters(distance)
    for upper_limit, fare in _TIER_BOUNDARIES_M:
        if meters < upper_limit:
            return fare
    return _EXTENDED_BASE_FARE + (meters - _EXTENDED_BASE_M) // _EXTENDED_STEP_M


def fare_tier(distance):
    """Return a human-readable description of the fare tier for a distance."""
    meters = _validated_meters(distance)
    if meters < 6000:
        return "Basic tier (0-6 km)"
    if meters < 12000:
        return "Progressive tier (6-12 km)"
    if meters < 22000:
        return "Progressive tier (12-22 km)"
    if meters < 32000:
        return "Progressive tier (22-32 km)"
    return "Extended tier (over 32 km)"


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes for a trip.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line changes on the route.

    Returns:
        Estimated travel time in minutes, rounded to one decimal place.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError("distance must be a non-negative finite number")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count cannot be negative")

    running_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = running_minutes + BOARDING_MINUTES + transfer_count * TRANSFER_MINUTES
    return round(total, 1)
