"""
Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometers):
    0-6 km   : 3 yuan
    6-12 km  : 4 yuan
    12-22 km : 5 yuan
    22-32 km : 6 yuan
    > 32 km  : +1 yuan for every additional 20 km (or part thereof)
"""

import math
from dataclasses import dataclass

# (upper bound km inclusive, fare yuan)
FARE_TIERS = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_KM = 20
EXTENDED_INCREMENT_YUAN = 1

AVERAGE_SPEED_KMH = 35.0        # average operating speed incl. stops
TRANSFER_TIME_MINUTES = 5.0     # average time per transfer


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError(f"Distance must be a number, got {distance!r}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    _validate_distance(distance)
    km = math.ceil(round(distance, 6) / 1000.0)
    for upper, fare in FARE_TIERS:
        if km <= upper:
            return fare
    extra_km = km - EXTENDED_BASE_KM
    increments = math.ceil(extra_km / EXTENDED_INCREMENT_KM)
    return EXTENDED_BASE_FARE + increments * EXTENDED_INCREMENT_YUAN


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance (meters) and number of transfers."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)) or transfer_count < 0:
        raise ValueError("Transfer count must be a non-negative number")
    travel = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(float(travel + transfer_count * TRANSFER_TIME_MINUTES), 1)


@dataclass
class FareResult:
    fare: int
    distance_km: float


def calculate_fare(distance):
    """Return a FareResult for a distance in meters."""
    return FareResult(fare=Sum_money(distance), distance_km=round(distance / 1000.0, 2))
