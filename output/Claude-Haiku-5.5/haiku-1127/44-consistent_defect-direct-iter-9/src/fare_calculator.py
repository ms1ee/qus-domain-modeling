"""Fare and travel time calculations for the Beijing Subway.

Fare structure (distances are rounded up to whole kilometers):
    0-6 km      : 3 yuan
    6-12 km     : 4 yuan
    12-22 km    : 5 yuan
    22-32 km    : 6 yuan
    over 32 km  : 6 yuan + 1 yuan for every additional 20 km (or part of it)
"""

import math


def Sum_money(distance):
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters.

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative or not finite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance) or distance < 0:
        raise ValueError("distance must be a finite non-negative number")

    # Ceiling rounding for fractional distances: any part of a kilometer counts.
    # Boundary values belong to the lower tier (e.g. exactly 6000 m -> 3 yuan).
    km = math.ceil(distance / 1000)

    if km <= 6:
        return 3
    if km <= 12:
        return 4
    if km <= 22:
        return 5
    if km <= 32:
        return 6
    return 6 + math.ceil((km - 32) / 20)


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated travel time in minutes.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / 1000.0) * 1.5 + transfer_count * 5.0
