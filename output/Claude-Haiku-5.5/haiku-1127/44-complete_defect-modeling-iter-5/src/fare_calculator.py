"""Beijing Subway fare calculation and travel-time estimation.

Fare structure (distance in kilometers, rounded up to a whole kilometer):
    0-6 km: 3 yuan
    6-12 km: 4 yuan
    12-22 km: 5 yuan
    22-32 km: 6 yuan
    beyond 32 km: 6 yuan + 1 yuan for every additional 20 km (or part thereof)
"""

import math

# (upper bound in km inclusive, fare in yuan), in ascending order.
FARE_TIERS = ((6, 3), (12, 4), (22, 5), (32, 6))
EXTENSION_START_KM = 32
EXTENSION_INTERVAL_KM = 20
EXTENSION_FARE_PER_INTERVAL = 1

AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 4.0


def Sum_money(distance):
    """Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters (fractional values are allowed;
            the distance is rounded up to whole kilometers).

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative or NaN.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number, got {type(distance).__name__}")
    if math.isnan(distance) or distance < 0:
        raise ValueError(f"Distance must be a non-negative number, got {distance}")

    km = math.ceil(distance / 1000.0)
    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    extra_km = km - EXTENSION_START_KM
    intervals = math.ceil(extra_km / EXTENSION_INTERVAL_KM)
    return FARE_TIERS[-1][1] + intervals * EXTENSION_FARE_PER_INTERVAL


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of line transfers on the route.

    Returns:
        float: Estimated travel time in minutes.

    Raises:
        ValueError: If distance is negative or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("Distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(travel_minutes + transfer_count * TRANSFER_TIME_MINUTES, 2)
