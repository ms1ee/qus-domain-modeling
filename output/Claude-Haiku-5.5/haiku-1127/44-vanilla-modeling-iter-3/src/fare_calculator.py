"""Beijing Subway fare calculation.

Fare tiers (left-closed, right-open intervals, in kilometers):
    [0, 6)     -> 3 yuan
    [6, 12)    -> 4 yuan
    [12, 22)   -> 5 yuan
    [22, 32)   -> 6 yuan
    [32, ...)  -> 7 yuan, plus 1 yuan for every further 20 km
                  (32-52 km: 7, 52-72 km: 8, ...)

Fractional distances are rounded up (ceiling) to the next whole meter before
the tier is looked up, so e.g. 5999.2 m is charged as 6000 m.
"""

import math
from dataclasses import dataclass
from typing import List, Optional

EXTENDED_STEP_KM = 20


@dataclass(frozen=True)
class FareRule:
    """One fare tier.

    Attributes:
        min_distance_km: Inclusive lower bound in kilometers.
        max_distance_km: Exclusive upper bound in kilometers, None if open-ended.
        fare_yuan: Fare charged within the tier (base fare for extended tier).
    """

    min_distance_km: float
    max_distance_km: Optional[float]
    fare_yuan: int


FARE_RULES: List[FareRule] = [
    FareRule(0, 6, 3),
    FareRule(6, 12, 4),
    FareRule(12, 22, 5),
    FareRule(22, 32, 6),
    FareRule(32, None, 7),
]

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance: float) -> int:
    """Compute the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters.

    Returns:
        The fare in yuan.

    Raises:
        TypeError: If distance is not a real number.
        ValueError: If distance is NaN, infinite or negative.
    """
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of meters")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must not be negative")

    meters = math.ceil(distance)
    for rule in FARE_RULES:
        if rule.max_distance_km is None:
            break
        low = int(round(rule.min_distance_km * 1000))
        high = int(round(rule.max_distance_km * 1000))
        if low <= meters < high:
            return rule.fare_yuan

    extended = FARE_RULES[-1]
    base_m = int(round(extended.min_distance_km * 1000))
    step_m = EXTENDED_STEP_KM * 1000
    return extended.fare_yuan + (meters - base_m) // step_m


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated time in minutes (about 1.5 min/km plus 5 min per transfer).

    Raises:
        ValueError: If distance or transfer_count is negative.
    """
    if distance < 0:
        raise ValueError("distance must not be negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must not be negative")
    return (distance / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
