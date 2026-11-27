"""Beijing Subway fare calculation and estimated travel time."""

import math

# Base fare tiers: (upper bound in km, inclusive) -> fare in yuan.
#   0-6 km: 3 yuan, 6-12 km: 4 yuan, 12-22 km: 5 yuan, 22-32 km: 6 yuan.
BASE_FARE_TIERS = ((6, 3), (12, 4), (22, 5), (32, 6))
# Beyond 32 km, one extra yuan for every 20 km (or fraction thereof).
EXTENSION_BASE_KM = 32
EXTENSION_STEP_KM = 20
EXTENSION_FARE_INCREMENT = 1

AVERAGE_SPEED_KMH = 35.0        # average in-train speed used for time estimation
TRANSFER_TIME_MINUTES = 5.0     # walking and waiting time per transfer


def Sum_money(distance):
    """Compute the subway fare in yuan for a trip of ``distance`` meters.

    Distances are rounded up to the next whole kilometer before tier lookup,
    so any fractional distance is charged as the next full kilometer.

    Args:
        distance: Travel distance in meters.

    Returns:
        Fare in yuan (int).

    Raises:
        ValueError: If distance is negative or not finite.
        TypeError: If distance is not a number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if not math.isfinite(distance) or distance < 0:
        raise ValueError("distance must be a finite non-negative number of meters")

    km = math.ceil(distance / 1000.0)
    for upper_km, fare in BASE_FARE_TIERS:
        if km <= upper_km:
            return fare
    extra_steps = math.ceil((km - EXTENSION_BASE_KM) / EXTENSION_STEP_KM)
    return BASE_FARE_TIERS[-1][1] + extra_steps * EXTENSION_FARE_INCREMENT


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers on the route.

    Returns:
        Estimated time in minutes (float, rounded to 2 decimals).
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
        raise ValueError("distance must be a non-negative number of meters")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(travel_minutes + transfer_count * TRANSFER_TIME_MINUTES, 2)
