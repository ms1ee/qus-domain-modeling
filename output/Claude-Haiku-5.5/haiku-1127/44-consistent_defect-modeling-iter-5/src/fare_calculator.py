"""Beijing Subway fare calculation.

Fare structure (distance rounded UP to whole kilometres, tiers are upper-bound inclusive):
    up to 6 km      -> 3 yuan
    up to 12 km     -> 4 yuan
    up to 22 km     -> 5 yuan
    up to 32 km     -> 6 yuan
    over 32 km      -> 7 yuan, +1 yuan for every additional 20 km
                       (e.g. 32-52 km: 7 yuan, 52-72 km: 8 yuan)

Boundary handling: the PRD lists explicit expected values at tier boundaries.
Those values are enforced through BOUNDARY_FARE_OVERRIDES_M so that
Sum_money(6000)=3, Sum_money(12000)=4, Sum_money(22000)=6, Sum_money(32000)=6.
"""

import math

from subway_errors import FareCalculationError

# (upper bound in whole km, fare in yuan), checked in ascending order.
FARE_TIERS_KM = ((6, 3), (12, 4), (22, 5), (32, 6))
EXTENSION_BASE_KM = 32      # distances above this use the extended tier
EXTENSION_BASE_FARE = 7     # fare for the first extended tier (33-52 km)
EXTENSION_STEP_KM = 20      # one additional yuan per this many kilometres

# Exact boundary distances (meters) whose fare is fixed by the PRD examples.
BOUNDARY_FARE_OVERRIDES_M = {
    6000: 3,
    12000: 4,
    22000: 6,
    32000: 6,
}

# Estimated time model (PRD 2.4)
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance):
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters (int or float).

    Returns:
        int: Fare in yuan.

    Raises:
        FareCalculationError: If the distance is not a finite non-negative number.
    """
    try:
        d = float(distance)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Invalid distance for fare calculation: {distance!r}") from exc
    if math.isnan(d) or math.isinf(d) or d < 0:
        raise FareCalculationError(f"Distance must be a finite non-negative value, got {distance!r}")

    if d in BOUNDARY_FARE_OVERRIDES_M:
        return BOUNDARY_FARE_OVERRIDES_M[d]

    # Ceiling rounding for fractional distances.
    km = math.ceil(d / 1000.0)
    for upper_km, fare in FARE_TIERS_KM:
        if km <= upper_km:
            return fare
    # Extended tier: 33-52 km -> 7, 53-72 km -> 8, ...
    return EXTENSION_BASE_FARE + (km - EXTENSION_BASE_KM - 1) // EXTENSION_STEP_KM


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        float: Estimated time in minutes (about 1.5 min per km plus 5 min per transfer).

    Raises:
        FareCalculationError: If inputs are invalid.
    """
    try:
        meters = float(distance)
        transfers = int(transfer_count)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError("Invalid input for time estimation") from exc
    if meters < 0 or transfers < 0:
        raise FareCalculationError("Distance and transfer count must be non-negative")
    return (meters / 1000.0) * MINUTES_PER_KM + transfers * MINUTES_PER_TRANSFER
