"""Beijing Subway fare and travel time estimation.

Fare structure (distance in meters, fractional meters are rounded up):
    0 to < 6 km       : 3 yuan
    6 km to < 12 km   : 4 yuan
    12 km to < 22 km  : 5 yuan
    22 km to < 32 km  : 6 yuan
    >= 32 km          : 7 yuan, plus 1 yuan for every further 20 km
"""

import math

BASE_FARE = 3
FARE_BREAKPOINTS_METERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
EXTENDED_START_METERS = 32000
EXTENDED_START_FARE = 7
EXTENDED_STEP_METERS = 20000

AVERAGE_SPEED_KMH = 35.0
BOARDING_MINUTES = 2.0
TRANSFER_MINUTES = 5.0


class FareCalculationError(ValueError):
    """Raised when a fare or time cannot be calculated from the given input."""


def _normalize_distance(distance) -> int:
    """Validate a distance in meters and round fractional values up."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("distance must be a finite number")
    if distance < 0:
        raise FareCalculationError("distance must not be negative")
    return math.ceil(distance)


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a trip of ``distance`` meters.

    Boundary values follow the official tiers: 6000 m costs 4 yuan,
    12000 m costs 5 yuan, 22000 m costs 6 yuan and 32000 m costs 7 yuan.
    """
    meters = _normalize_distance(distance)
    for limit, fare in FARE_BREAKPOINTS_METERS:
        if meters < limit:
            return fare
    return EXTENDED_START_FARE + (meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS


def fare_tier_name(distance) -> str:
    """Return a human-readable name of the fare tier for ``distance``."""
    meters = _normalize_distance(distance)
    if meters < 6000:
        return "Basic tier (0-6 km)"
    if meters < 12000:
        return "Progressive tier (6-12 km)"
    if meters < 22000:
        return "Progressive tier (12-22 km)"
    if meters < 32000:
        return "Progressive tier (22-32 km)"
    return "Extended tier (over 32 km)"


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate the travel time in minutes.

    The estimate combines average running speed, a fixed boarding allowance
    and a penalty for each line transfer.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of line transfers.

    Returns:
        Estimated time in minutes, rounded to one decimal place.
    """
    meters = _normalize_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise FareCalculationError("transfer_count must be an integer")
    if transfer_count < 0:
        raise FareCalculationError("transfer_count must not be negative")
    running = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    minutes = running + BOARDING_MINUTES + transfer_count * TRANSFER_MINUTES
    return round(minutes, 1)
