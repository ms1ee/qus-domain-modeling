"""Fare calculation following the Beijing Subway distance-based fare structure.

    [0, 6) km   -> 3 yuan
    [6, 12) km  -> 4 yuan
    [12, 22) km -> 5 yuan
    [22, 32) km -> 6 yuan
    >= 32 km    -> 7 yuan, +1 yuan for every further 20 km

Fractional distances (meters) are rounded up before mapping.
"""

import math

# (exclusive upper bound in meters, fare in yuan)
FARE_TABLE = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_START_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_METERS = 20000

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


class FareCalculationError(ValueError):
    """Raised when a fare cannot be calculated for the given input."""


def _validate_distance(distance):
    if isinstance(distance, bool):
        raise FareCalculationError("Distance must be a number")
    if isinstance(distance, str):
        try:
            distance = float(distance.strip())
        except ValueError as exc:
            raise FareCalculationError(f"Invalid distance: {distance!r}") from exc
    if not isinstance(distance, (int, float)):
        raise FareCalculationError(f"Distance must be a number, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError("Distance must be finite")
    if distance < 0:
        raise FareCalculationError("Distance must not be negative")
    return distance


def Sum_money(distance):
    """Return the fare (yuan) for a travel distance given in meters."""
    distance = _validate_distance(distance)
    meters = int(math.ceil(distance))
    for upper, fare in FARE_TABLE:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfers."""
    distance = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise FareCalculationError("Transfer count must be a non-negative integer")
    ride = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(ride + transfer_count * TRANSFER_TIME_MINUTES, 1)
