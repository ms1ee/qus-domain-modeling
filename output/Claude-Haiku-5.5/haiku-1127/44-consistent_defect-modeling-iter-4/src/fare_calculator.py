"""Beijing Subway fare calculation.

Fare structure (distances are rounded up to whole kilometres, so any
fractional distance is charged as the next full kilometre):

    * 0 - 6 km      : 3 yuan
    * 6 - 12 km     : 4 yuan
    * 12 - 22 km    : 5 yuan
    * 22 - 32 km    : 6 yuan
    * over 32 km    : 7 yuan for 32-52 km, 8 yuan for 52-72 km, ...
                      i.e. +1 yuan for every further 20 km.

Boundary values follow the PRD examples exactly:
    6000 m -> 3 yuan, 12000 m -> 4 yuan, 22000 m -> 6 yuan, 32000 m -> 6 yuan.
"""

import math

MINUTES_PER_KM = 1.5          # average riding time per kilometre
MINUTES_PER_TRANSFER = 5.0    # average time spent per line transfer

# Human-readable description of the fare tiers, expressed on whole kilometres.
FARE_TIERS = (
    ("basic", 0, 6, 3),
    ("progressive", 7, 12, 4),
    ("progressive", 13, 22, 5),
    ("progressive", 23, 32, 6),
    ("extended", 33, None, 7),   # +1 yuan per 20 km beyond 32 km
)


class FareCalculationError(ValueError):
    """Raised when a fare cannot be calculated for the given input."""


def Sum_money(distance):
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: travelled distance in meters (int or float, non-negative).

    Returns:
        int: fare in yuan.

    Raises:
        TypeError: if distance is not a number.
        ValueError: if distance is negative or NaN.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or distance < 0:
        raise ValueError("distance must be a non-negative number of meters")

    # Ceiling rounding for fractional distances: any part of a kilometre is charged.
    kilometres = math.ceil(distance / 1000.0)

    if kilometres <= 6:
        return 3
    if kilometres <= 12:
        return 4
    if kilometres < 22:
        return 5
    if kilometres <= 32:
        return 6
    # Extended tier: 7 yuan for 33-52 km, 8 yuan for 53-72 km, ...
    return 7 + (kilometres - 33) // 20


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time of a route.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line transfers.

    Returns:
        float: estimated time in minutes (about 1.5 min per km plus 5 min per transfer).
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
