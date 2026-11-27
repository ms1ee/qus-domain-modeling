"""
Beijing Subway fare calculation.

Fare structure:
    0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan,
    above 32 km: +1 yuan for every (started) 20 km.
Distances are rounded up to the next whole kilometer.
"""

import math

# (upper bound in km inclusive, fare in yuan)
FARE_TIERS = [(6, 3), (12, 4), (22, 5), (32, 6)]
BASE_EXTENDED_FARE = 6
EXTENDED_THRESHOLD_KM = 32
EXTENDED_STEP_KM = 20

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def distance_to_km(distance):
    """Convert meters to whole kilometers, rounding up."""
    _validate_distance(distance)
    if isinstance(distance, int):
        return -(-distance // 1000)
    return math.ceil(distance / 1000.0)


def Sum_money(distance):
    """Return the fare in yuan for a distance given in meters."""
    km = distance_to_km(distance)
    for limit, fare in FARE_TIERS:
        if km <= limit:
            return fare
    extra = math.ceil((km - EXTENDED_THRESHOLD_KM) / EXTENDED_STEP_KM)
    return BASE_EXTENDED_FARE + extra


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for a distance in meters."""
    _validate_distance(distance)
    if transfer_count is None:
        transfer_count = 0
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    minutes += transfer_count * TRANSFER_TIME_MINUTES
    return round(float(minutes), 1)


def format_fare(fare):
    return f"Fare: {fare} yuan"
