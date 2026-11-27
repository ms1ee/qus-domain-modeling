"""Fare calculation according to the Beijing Subway fare structure.

Fare tiers (distance lower bound in meters -> fare in yuan):
    0 m       -> 3 yuan   (basic tier, 0-6 km)
    6000 m    -> 4 yuan   (progressive tier, 6-12 km)
    12000 m   -> 5 yuan   (progressive tier, 12-22 km)
    22000 m   -> 6 yuan   (progressive tier, 22-32 km)
    32000 m   -> 7 yuan   (extended tier start)
Beyond 32 km the fare increases by 1 yuan for every further 20 km.
Fractional distances are rounded up to the next whole meter.
"""

import math

# (lower bound in meters, fare in yuan); must be sorted ascending.
FARE_TIERS = (
    (0, 3),
    (6000, 4),
    (12000, 5),
    (22000, 6),
    (32000, 7),
)

EXTENDED_TIER_START_M = 32000
EXTENDED_STEP_M = 20000

# Average operating speed and fixed time components for travel estimation.
AVERAGE_SPEED_KMH = 35.0
BOARDING_MINUTES = 2.0
TRANSFER_MINUTES = 5.0


def Sum_money(distance):
    """Return the subway fare in yuan for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float, non-negative).

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)
    fare = FARE_TIERS[0][1]
    for lower_bound, price in FARE_TIERS:
        if meters >= lower_bound:
            fare = price
    if meters >= EXTENDED_TIER_START_M:
        fare += (meters - EXTENDED_TIER_START_M) // EXTENDED_STEP_M
    return int(fare)


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    The estimate combines the in-train time at an average speed, a fixed
    boarding allowance and a walking allowance for every transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of line changes on the route.

    Returns:
        float: Estimated travel time in minutes, rounded to one decimal place.

    Raises:
        TypeError: If the arguments are not numeric.
        ValueError: If the distance is negative or the transfer count is invalid.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if distance < 0:
        raise ValueError("distance must not be negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")

    travel_minutes = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_MINUTES + travel_minutes + transfer_count * TRANSFER_MINUTES
    return round(total, 1)
