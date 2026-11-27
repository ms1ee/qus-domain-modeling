"""Beijing Subway fare calculation and trip time estimation."""

import math

# Average travel speed assumption and time penalty per transfer.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5


def Sum_money(distance) -> int:
    """Return the fare in yuan for a trip of ``distance`` meters.

    Fare tiers:
        0 - 6 km        : 3 yuan
        6 - 12 km       : 4 yuan
        12 - 22 km      : 5 yuan
        22 - 32 km      : 6 yuan
        over 32 km      : 7 yuan, plus 1 yuan for every further 20 km
                          (32-52 km: 7, 52-72 km: 8, ...)

    Boundary values follow the examples given in the requirements:
        6000 m -> 3 yuan, 12000 m -> 4 yuan, 22000 m -> 6 yuan,
        32000 m -> 6 yuan.

    Fractional distances are rounded up (ceiling) before the lookup.

    Args:
        distance: Trip distance in meters (int or float).

    Returns:
        Fare in yuan as an integer.

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is negative, NaN or infinite.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")

    meters = math.ceil(distance)

    if meters <= 6000:
        return 3
    if meters <= 12000:
        return 4
    if meters < 22000:
        return 5
    if meters <= 32000:
        return 6
    # Extended tier: 7 yuan at 32 km, +1 yuan every 20 km.
    return 7 + (meters - 32000) // 20000


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate the travel time in minutes.

    Uses approximately 1.5 minutes per kilometre plus approximately
    5 minutes per transfer.

    Args:
        distance: Trip distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated time in minutes, rounded to two decimals.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    minutes = (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
    return round(minutes, 2)
