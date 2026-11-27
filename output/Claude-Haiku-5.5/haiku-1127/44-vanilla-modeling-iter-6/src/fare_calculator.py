"""Fare calculation based on the Beijing Subway fare structure."""

import math

from models import FareTier
from subway_errors import FareCalculationError

# Fare table: left-closed, right-open distance intervals (kilometers).
FARE_TIERS = (
    FareTier(0.0, 6.0, 3, 0.0),
    FareTier(6.0, 12.0, 4, 0.0),
    FareTier(12.0, 22.0, 5, 0.0),
    FareTier(22.0, 32.0, 6, 0.0),
    FareTier(32.0, math.inf, 7, 20.0),
)

# Time model constants used for estimated travel time.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Return the fare in yuan for a travel distance given in meters.

    The distance is first rounded up to a whole number of meters (ceiling
    rounding of fractional distances). Intervals are left-closed, so a
    boundary value such as 6000 m is charged at the next higher tier.

    Args:
        distance: travelled distance in meters.

    Returns:
        Fare in yuan as an int.

    Raises:
        FareCalculationError: if the distance is not a finite non-negative number.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise FareCalculationError("distance must be a number of meters")
    if not math.isfinite(distance) or distance < 0:
        raise FareCalculationError("distance must be a finite non-negative value")

    meters = math.ceil(distance)
    for tier in FARE_TIERS:
        low = tier.min_distance_km * 1000
        high = tier.max_distance_km * 1000
        if low <= meters < high:
            if tier.extension_interval_km > 0:
                step = tier.extension_interval_km * 1000
                return tier.price + int((meters - low) // step)
            return tier.price
    # Unreachable because the last tier extends to infinity.
    raise FareCalculationError(f"no fare tier matches distance {distance}")


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line transfers.

    Returns:
        Estimated time in minutes (about 1.5 min per km plus 5 min per transfer).

    Raises:
        FareCalculationError: for invalid inputs.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)) \
            or not math.isfinite(distance) or distance < 0:
        raise FareCalculationError("distance must be a finite non-negative number")
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) \
            or transfer_count < 0:
        raise FareCalculationError("transfer_count must be a non-negative integer")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
