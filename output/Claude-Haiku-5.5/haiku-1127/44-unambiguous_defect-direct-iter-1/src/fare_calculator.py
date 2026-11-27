"""Beijing Subway fare calculation and travel-time estimation."""

import math

# Distance tier boundaries in meters and the fare for each tier.
BASIC_TIER_LIMIT_M = 6000       # 0 - 6 km: 3 yuan
PROGRESSIVE_TIER_1_M = 12000    # 6 - 12 km: 4 yuan
PROGRESSIVE_TIER_2_M = 22000    # 12 - 22 km: 5 yuan
PROGRESSIVE_TIER_3_M = 32000    # 22 - 32 km: 6 yuan
EXTENDED_BASE_FARE = 7          # >= 32 km: 7 yuan, +1 yuan per 20 km beyond 32 km
EXTENDED_STEP_M = 20000

# Travel-time model parameters.
AVERAGE_SPEED_KMH = 35.0        # average in-service speed including station dwell time
BOARDING_WAIT_MIN = 3.0         # average initial waiting time
TRANSFER_TIME_MIN = 5.0         # average time per transfer (walking + waiting)


def Sum_money(distance):
    """Calculate the subway fare for a trip of `distance` meters.

    Fractional meters are rounded up to the next whole meter before tier lookup.
    Boundary handling (lower bound inclusive):
        < 6000 m          -> 3 yuan
        6000 - 11999 m    -> 4 yuan
        12000 - 21999 m   -> 5 yuan
        22000 - 31999 m   -> 6 yuan
        >= 32000 m       -> 7 yuan, +1 yuan for every further 20 km

    Args:
        distance: travel distance in meters (int or float, non-negative).

    Returns:
        Fare as an integer number of yuan.

    Raises:
        TypeError: if distance is not a real number.
        ValueError: if distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    meters = int(math.ceil(distance))
    if meters < BASIC_TIER_LIMIT_M:
        return 3
    if meters < PROGRESSIVE_TIER_1_M:
        return 4
    if meters < PROGRESSIVE_TIER_2_M:
        return 5
    if meters < PROGRESSIVE_TIER_3_M:
        return 6
    return EXTENDED_BASE_FARE + (meters - PROGRESSIVE_TIER_3_M) // EXTENDED_STEP_M


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Time = boarding wait + riding time at average speed + transfer_count * transfer time.

    Args:
        distance: travel distance in meters (non-negative).
        transfer_count: number of transfers (non-negative integer).

    Returns:
        Estimated travel time in minutes, rounded to one decimal place.

    Raises:
        TypeError / ValueError on invalid arguments.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if math.isnan(distance) or math.isinf(distance) or distance < 0:
        raise ValueError("distance must be a finite non-negative number")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")

    if distance == 0 and transfer_count == 0:
        return 0.0

    riding_min = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_WAIT_MIN + riding_min + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
