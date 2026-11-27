"""Beijing Subway fare calculation.

Fare structure (distance in kilometers):
    [0, 6)   -> 3 yuan
    [6, 12)  -> 4 yuan
    [12, 22) -> 5 yuan
    [22, 32) -> 6 yuan
    >= 32    -> 7 yuan, plus 1 yuan for every further 20 km
Boundary values move into the higher tier (6 km = 4 yuan, 32 km = 7 yuan).
Fractional distances (meters) are rounded up.
"""

import math

# (exclusive upper bound in meters, fare in yuan)
FARE_TIERS = [
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
]
EXTENDED_START = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP = 20000

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


class FareCalculationError(Exception):
    """Raised when a fare cannot be computed."""


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number, got {distance!r}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError(f"Distance must be finite, got {distance!r}")
    if distance < 0:
        raise ValueError(f"Distance must be non-negative, got {distance!r}")


def Sum_money(distance):
    """Return the fare (yuan) for a trip of ``distance`` meters."""
    _validate_distance(distance)
    meters = math.ceil(distance)
    for upper, fare in FARE_TIERS:
        if meters < upper:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START) // EXTENDED_STEP


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Based on an average running speed (including stops) of 35 km/h plus
    5 minutes per transfer.
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)):
        raise TypeError("transfer_count must be a number")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    minutes += transfer_count * TRANSFER_TIME_MINUTES
    return round(float(minutes), 1)


def fare_table():
    """Return a human-readable description of the fare structure."""
    rows = []
    lower = 0
    for upper, fare in FARE_TIERS:
        rows.append(f"{lower // 1000}-{upper // 1000} km: {fare} yuan")
        lower = upper
    rows.append(
        f"Over {EXTENDED_START // 1000} km: {EXTENDED_BASE_FARE} yuan, "
        f"+1 yuan per additional {EXTENDED_STEP // 1000} km"
    )
    return rows
