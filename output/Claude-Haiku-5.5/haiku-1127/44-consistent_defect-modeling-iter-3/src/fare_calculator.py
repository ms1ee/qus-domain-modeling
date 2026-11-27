"""Beijing Subway fare calculation.

Distances are converted to chargeable kilometers by rounding up (ceiling),
and the tier is chosen from that integer kilometer value:

* up to 6 km: 3 yuan
* up to 12 km: 4 yuan
* up to 21 km (i.e. under 22 km): 5 yuan
* up to 32 km: 6 yuan
* over 32 km: 7 yuan for 33-52 km, then +1 yuan per further 20 km
  (53-72 km: 8 yuan, and so on)

This satisfies the PRD boundary examples: 6000 m -> 3, 12000 m -> 4,
22000 m -> 6, 32000 m -> 6.
"""

import math
from dataclasses import dataclass

# Basic and progressive tiers: (maximum chargeable km inclusive, price in yuan).
BASE_FARE_TIERS = ((6, 3), (12, 4), (21, 5), (32, 6))

# Extended tier parameters.
EXTENDED_START_KM = 32
EXTENDED_BASE_PRICE = 6
EXTENDED_STEP_KM = 20

# Travel time model.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


@dataclass(frozen=True)
class FareResult:
    """Result of a fare calculation.

    Attributes:
        fare_yuan: Fare in yuan.
        chargeable_distance_m: Distance used for charging (rounded up to whole km), in meters.
    """

    fare_yuan: int
    chargeable_distance_m: int


def _validate_distance(distance):
    """Validate a distance in meters."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"distance must be a number of meters, got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")


def calculate_fare(distance) -> FareResult:
    """Compute the fare and chargeable distance for a distance in meters."""
    _validate_distance(distance)
    chargeable_km = math.ceil(distance / 1000)

    for max_km, price in BASE_FARE_TIERS:
        if chargeable_km <= max_km:
            return FareResult(price, chargeable_km * 1000)

    # Extended tier: over 32 km.
    steps = (chargeable_km - EXTENDED_START_KM - 1) // EXTENDED_STEP_KM
    price = EXTENDED_BASE_PRICE + 1 + steps
    return FareResult(price, chargeable_km * 1000)


def Sum_money(distance) -> int:
    """Return the fare in yuan for a distance given in meters."""
    return calculate_fare(distance).fare_yuan


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: Distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated time in minutes (about 1.5 min per km plus 5 min per transfer).
    """
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    return float(distance / 1000 * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER)
