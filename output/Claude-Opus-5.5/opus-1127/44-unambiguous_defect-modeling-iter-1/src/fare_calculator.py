"""
Fare calculation based on the Beijing Subway fare structure.

    0  - 6 km   : 3 yuan
    6  - 12 km  : 4 yuan
    12 - 22 km  : 5 yuan
    22 - 32 km  : 6 yuan
    >= 32 km    : 7 yuan, +1 yuan for every additional 20 km

Boundary values belong to the upper tier (6000 m -> 4 yuan, 12000 -> 5,
22000 -> 6, 32000 -> 7). Fractional distances are rounded up to whole meters.
"""

import math


class FareCalculationError(ValueError, TypeError):
    """Raised for invalid distance input."""


#: (tier name, min meters inclusive, max meters exclusive, fare)
FARE_TIERS = [
    ("Basic", 0, 6000, 3),
    ("Progressive", 6000, 12000, 4),
    ("Progressive", 12000, 22000, 5),
    ("Progressive", 22000, 32000, 6),
]
EXTENDED_THRESHOLD_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_METERS = 20000

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


class FareStructure:
    """Container exposing the fare tiers (domain model helper)."""

    tiers = FARE_TIERS
    extended_threshold_km = EXTENDED_THRESHOLD_METERS // 1000
    extended_increment_km = EXTENDED_INCREMENT_METERS // 1000

    def fare(self, distance):
        return Sum_money(distance)


def _normalize_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError(f"Distance must be a number, got {distance!r}")
    if math.isnan(distance) or math.isinf(distance):
        raise FareCalculationError(f"Distance must be finite, got {distance!r}")
    if distance < 0:
        raise FareCalculationError(f"Distance cannot be negative, got {distance!r}")
    return math.ceil(distance)


def Sum_money(distance):
    """
    Calculate the fare (yuan) for a distance in meters.

    :raises FareCalculationError: (a ValueError/TypeError) for invalid input
    """
    d = _normalize_distance(distance)
    for _name, low, high, fare in FARE_TIERS:
        if low <= d < high:
            return fare
    extra = (d - EXTENDED_THRESHOLD_METERS) // EXTENDED_INCREMENT_METERS
    return EXTENDED_BASE_FARE + int(extra)


def get_fare_tier(distance):
    """Return the tier name ('Basic', 'Progressive' or 'Extended')."""
    d = _normalize_distance(distance)
    for name, low, high, _fare in FARE_TIERS:
        if low <= d < high:
            return name
    return "Extended"


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate travel time in minutes from distance (meters) and transfer count.
    Uses an average speed of 35 km/h plus 5 minutes per transfer.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0 \
            or math.isnan(distance):
        raise FareCalculationError(f"Invalid distance {distance!r}")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise FareCalculationError(f"Invalid transfer count {transfer_count!r}")
    ride = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(ride + transfer_count * TRANSFER_TIME_MINUTES, 1)
