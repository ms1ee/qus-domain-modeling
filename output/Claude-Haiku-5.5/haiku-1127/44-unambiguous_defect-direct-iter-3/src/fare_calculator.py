"""Beijing Subway fare and travel-time estimation.

Fare structure:
  * 0 - 6 km      : 3 yuan
  * 6 - 12 km     : 4 yuan
  * 12 - 22 km    : 5 yuan
  * 22 - 32 km    : 6 yuan
  * over 32 km    : 7 yuan, plus 1 yuan for every further 20 km

Boundary values belong to the higher tier (6000 m -> 4 yuan, 32000 m -> 7 yuan).
Fractional distances are rounded up to the next whole metre before lookup.
"""

from __future__ import annotations

import math
from typing import Tuple

BASIC_FARE_TIERS: Tuple[Tuple[int, int], ...] = (
    (6000, 3),    # distances below 6000 m
    (12000, 4),   # 6000 m up to 12000 m
    (22000, 5),   # 12000 m up to 22000 m
    (32000, 6),   # 22000 m up to 32000 m
)
EXTENDED_BASE_DISTANCE_M: int = 32000
EXTENDED_BASE_FARE: int = 7
EXTENDED_STEP_DISTANCE_M: int = 20000

AVERAGE_SPEED_KMH: float = 35.0   # average operating speed of urban subway trains
BOARDING_TIME_MIN: float = 2.0    # fixed time for entering the system
TRANSFER_TIME_MIN: float = 4.0    # walking and waiting time per transfer


def _validate_distance(distance: float) -> float:
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number of metres")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    return float(distance)


def Sum_money(distance: float) -> int:
    """Return the subway fare in yuan for a travelled ``distance`` in metres."""
    metres = math.ceil(_validate_distance(distance))
    for upper_bound, fare in BASIC_FARE_TIERS:
        if metres < upper_bound:
            return fare
    extra_steps = (metres - EXTENDED_BASE_DISTANCE_M) // EXTENDED_STEP_DISTANCE_M
    return EXTENDED_BASE_FARE + extra_steps


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes from distance (metres) and transfers."""
    metres = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("transfer_count must be an integer")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    travel_min = (metres / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_TIME_MIN + travel_min + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
