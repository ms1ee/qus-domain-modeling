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

# (max distance in km inclusive, fare in yuan)
FARE_TIERS = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_KM = 20
EXTENDED_INCREMENT_FARE = 1

# Estimated time parameters
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be finite")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def distance_to_km_ceil(distance):
    """Convert meters to kilometers rounding up to a whole kilometer."""
    _validate_distance(distance)
    return int(math.ceil(distance / 1000.0))


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    km = distance_to_km_ceil(distance)
    for max_km, fare in FARE_TIERS:
        if km <= max_km:
            return fare
    extra = km - EXTENDED_BASE_KM
    increments = int(math.ceil(extra / EXTENDED_INCREMENT_KM))
    return EXTENDED_BASE_FARE + increments * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes for a distance (meters) and transfers."""
    _validate_distance(distance)
    if transfer_count is None or transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    ride = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(ride + transfer_count * TRANSFER_TIME_MINUTES, 1)


class FareCalculator:
    """Object-oriented wrapper around the fare structure."""

    rounding_mode = "ceil"

    def calculate(self, distance):
        return Sum_money(distance)

    def format_fare(self, distance):
        return f"Fare: {Sum_money(distance)} yuan"
