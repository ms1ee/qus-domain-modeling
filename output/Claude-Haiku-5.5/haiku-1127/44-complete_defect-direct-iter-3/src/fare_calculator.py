"""
Fare calculation for the Beijing Subway.

Fare structure:
    0-6 km    : 3 yuan
    6-12 km   : 4 yuan
    12-22 km  : 5 yuan
    22-32 km  : 6 yuan
    over 32 km: 6 yuan plus 1 yuan for every additional 20 km (or part thereof)

Fractional kilometers are rounded up before a tier is selected.
"""

import math

# (inclusive upper bound in km, fare in yuan) for the progressive tiers.
FARE_TIERS = [(6, 3), (12, 4), (22, 5), (32, 6)]
EXTENSION_BASE_KM = 32
EXTENSION_STEP_KM = 20

# Estimated time model parameters.
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MIN = 5.0


def _ceil_kilometers(distance):
    """Convert meters to whole kilometers, rounding fractional values up."""
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    return math.ceil(distance / 1000)


def Sum_money(distance):
    """
    Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters.

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is negative.
    """
    km = _ceil_kilometers(distance)
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare
    extra_steps = math.ceil((km - EXTENSION_BASE_KM) / EXTENSION_STEP_KM)
    return FARE_TIERS[-1][1] + extra_steps


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate the travel time of a route.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of line transfers on the route.

    Returns:
        float: Estimated travel time in minutes, rounded to two decimals.

    Raises:
        ValueError: If distance or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    travel_minutes = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(travel_minutes + transfer_count * TRANSFER_TIME_MIN, 2)
