"""Fare calculation based on the Beijing Subway fare structure.

Fare tiers (distance in meters, lower bound inclusive):
    0 - 6 km        3 yuan
    6 - 12 km       4 yuan
    12 - 22 km      5 yuan
    22 - 32 km      6 yuan
    over 32 km      7 yuan, plus 1 yuan for every further 20 km
Fractional meters are rounded up to the next whole meter before lookup.
"""

import math


# (lower bound in meters, fare in yuan) for the basic and progressive tiers.
FARE_TIERS = (
    (0, 3),
    (6000, 4),
    (12000, 5),
    (22000, 6),
)
EXTENDED_THRESHOLD_M = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_M = 20000

# Time model used for the estimated travel time.
AVERAGE_SPEED_KMH = 35.0
BOARDING_TIME_MIN = 2.0
TRANSFER_TIME_MIN = 4.0


def Sum_money(distance):
    """Return the subway fare in yuan for a travel distance in meters.

    Raises ValueError for negative or non-numeric distances.
    """
    try:
        meters = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"distance must be a number of meters: {distance!r}") from exc
    if math.isnan(meters) or math.isinf(meters):
        raise ValueError("distance must be a finite number")
    if meters < 0:
        raise ValueError("distance must not be negative")

    whole_meters = math.ceil(meters)

    fare = FARE_TIERS[0][1]
    for lower_bound, price in FARE_TIERS:
        if whole_meters >= lower_bound:
            fare = price

    if whole_meters >= EXTENDED_THRESHOLD_M:
        extra_steps = (whole_meters - EXTENDED_THRESHOLD_M) // EXTENDED_STEP_M
        fare = EXTENDED_BASE_FARE + extra_steps
    return int(fare)


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    The estimate combines running time at an average speed, a boarding
    allowance, and a fixed waiting/walking time for every transfer.
    Returns a float rounded to one decimal place.
    """
    try:
        meters = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"distance must be a number of meters: {distance!r}") from exc
    if meters < 0:
        raise ValueError("distance must not be negative")
    if transfer_count < 0:
        raise ValueError("transfer count must not be negative")

    running = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = running + BOARDING_TIME_MIN + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
