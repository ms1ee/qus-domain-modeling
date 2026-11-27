"""
Fare calculation module implementing the Beijing Subway fare structure.

    0  - 6  km : 3 yuan
    6  - 12 km : 4 yuan
    12 - 22 km : 5 yuan
    22 - 32 km : 6 yuan
    > 32 km    : 6 yuan + 1 yuan per (started) additional 20 km
                 (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...)

Intervals are left-closed and right-open, i.e. boundary values are charged
according to the next higher tier.  Fractional distances (meters) are
rounded up before evaluation.
"""

from __future__ import annotations

import math

# (lower bound inclusive, upper bound exclusive, fare) in meters / yuan
FARE_TIERS = [
    (0, 6000, 3),
    (6000, 12000, 4),
    (12000, 22000, 5),
    (22000, 32000, 6),
]
EXTENDED_START = 32000
EXTENDED_STEP = 20000
EXTENDED_BASE_FARE = 7

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def _validate_number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
    return value


def Sum_money(distance) -> int:
    """Return the fare (yuan) for a travel distance given in meters."""
    _validate_number(distance, "distance")
    meters = math.ceil(distance)
    for low, high, fare in FARE_TIERS:
        if low <= meters < high:
            return fare
    return EXTENDED_BASE_FARE + (meters - EXTENDED_START) // EXTENDED_STEP


def calculate_fare(distance) -> int:
    """Alias of :func:`Sum_money`."""
    return Sum_money(distance)


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated travel time in minutes.

    ~1.5 minutes per kilometer plus ~5 minutes per transfer.
    """
    _validate_number(distance, "distance")
    _validate_number(transfer_count, "transfer_count")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
