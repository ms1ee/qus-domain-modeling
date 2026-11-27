"""Fare and travel time calculation for the Beijing Subway.

Fare structure (distance in kilometers, rounded up):
    0-6 km:   3 yuan
    6-12 km:  4 yuan
    12-22 km: 5 yuan
    22-32 km: 6 yuan
    beyond 32 km: 6 yuan + 1 yuan for every additional (started) 20 km
"""

import math

# (inclusive upper bound in km, fare in yuan), in ascending order.
FARE_TIERS = ((6, 3), (12, 4), (22, 5), (32, 6))
EXTENSION_START_KM = 32
EXTENSION_STEP_KM = 20
EXTENSION_STEP_FARE = 1

AVERAGE_SPEED_KMH = 35.0    # average operating speed including stops
TRANSFER_TIME_MIN = 4.0     # walking/waiting time per transfer
BOARDING_TIME_MIN = 2.0     # fixed boarding overhead per trip


def Sum_money(distance) -> int:
    """Return the subway fare in yuan for a trip of ``distance`` meters.

    Fractional kilometers are rounded up (ceiling) before mapping to a tier.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"distance must be a number, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    km = math.ceil(distance / 1000)

    for upper_km, fare in FARE_TIERS:
        if km <= upper_km:
            return fare

    extra_km = km - EXTENSION_START_KM
    steps = math.ceil(extra_km / EXTENSION_STEP_KM)
    base_fare = FARE_TIERS[-1][1]
    return base_fare + steps * EXTENSION_STEP_FARE


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate the travel time in minutes.

    Args:
        distance: Total distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated travel time in minutes, rounded to one decimal place.

    Raises:
        ValueError: If distance or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")

    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_TIME_MIN + travel_minutes + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
