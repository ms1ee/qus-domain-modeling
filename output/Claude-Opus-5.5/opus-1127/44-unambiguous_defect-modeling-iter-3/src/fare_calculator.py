"""Beijing Subway fare calculation.

Fare structure (distance in meters, upper bounds exclusive):
    [0, 6000)       3 yuan   basic tier
    [6000, 12000)   4 yuan   progressive tier
    [12000, 22000)  5 yuan   progressive tier
    [22000, 32000)  6 yuan   progressive tier
    >= 32000        7 yuan + 1 yuan per further full 20 km (extended tier)

Fractional distances are rounded up to the next whole meter.
"""

import math

FARE_TIERS = [
    {"min_distance": 0, "max_distance": 6000, "fare": 3, "tier_type": "basic"},
    {"min_distance": 6000, "max_distance": 12000, "fare": 4, "tier_type": "progressive"},
    {"min_distance": 12000, "max_distance": 22000, "fare": 5, "tier_type": "progressive"},
    {"min_distance": 22000, "max_distance": 32000, "fare": 6, "tier_type": "progressive"},
]
EXTENDED_START_DISTANCE = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_INCREMENT_DISTANCE = 20000
EXTENDED_INCREMENT_FARE = 1

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


class FareCalculationError(Exception):
    """Raised when a fare cannot be calculated."""


def _normalize_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    return math.ceil(distance)


def get_fare_tier(distance):
    """Return the tier type ('basic', 'progressive', 'extended') for a distance."""
    d = _normalize_distance(distance)
    for tier in FARE_TIERS:
        if tier["min_distance"] <= d < tier["max_distance"]:
            return tier["tier_type"]
    return "extended"


def Sum_money(distance):
    """Return the fare in yuan for a distance given in meters."""
    d = _normalize_distance(distance)
    for tier in FARE_TIERS:
        if tier["min_distance"] <= d < tier["max_distance"]:
            return tier["fare"]
    extra = (d - EXTENDED_START_DISTANCE) // EXTENDED_INCREMENT_DISTANCE
    return EXTENDED_BASE_FARE + int(extra) * EXTENDED_INCREMENT_FARE


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes.

    Based on an average operating speed (including stops) of 35 km/h plus
    5 minutes per transfer.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, (int, float)):
        raise TypeError("Transfer count must be a number")
    if distance < 0 or transfer_count < 0:
        raise ValueError("Distance and transfer count must be non-negative")
    travel = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(travel + transfer_count * TRANSFER_TIME_MINUTES, 1)


def format_fare(fare):
    return f"Fare: {fare} yuan"
