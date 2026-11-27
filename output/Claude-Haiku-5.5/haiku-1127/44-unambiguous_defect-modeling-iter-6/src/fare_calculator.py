"""Fare and travel-time calculation for the Beijing Subway."""

import math
from dataclasses import dataclass
from typing import List

AVERAGE_SPEED_METERS_PER_MINUTE = 500.0   # average speed including stops (~30 km/h)
BOARDING_MINUTES = 3.0                    # fixed boarding/waiting allowance
TRANSFER_MINUTES = 5.0                    # time spent per line change


@dataclass(frozen=True)
class FareRule:
    """Fare for a distance band.

    The band is [min_distance_meters, max_distance_meters).
    """

    min_distance_meters: float
    max_distance_meters: float
    fare_yuan: int


BASIC_FARE_RULES = (
    FareRule(0.0, 6000.0, 3),
    FareRule(6000.0, 12000.0, 4),
    FareRule(12000.0, 22000.0, 5),
    FareRule(22000.0, 32000.0, 6),
)

EXTENDED_BASE_DISTANCE_METERS = 32000.0
EXTENDED_BASE_FARE_YUAN = 7
EXTENDED_STEP_METERS = 20000.0
EXTENDED_STEP_FARE_YUAN = 1


def fare_rules() -> List[FareRule]:
    """Return the basic fare bands (the extended tier is computed by formula)."""
    return list(BASIC_FARE_RULES)


def _validate_distance(distance) -> float:
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number of meters")
    if not math.isfinite(distance) or distance < 0:
        raise ValueError("Distance must be a finite non-negative number")
    return float(distance)


def Sum_money(distance) -> int:
    """Return the fare in yuan for a travelled distance in meters.

    Rules:
        [0, 6000)        -> 3 yuan
        [6000, 12000)    -> 4 yuan
        [12000, 22000)   -> 5 yuan
        [22000, 32000)   -> 6 yuan
        >= 32000         -> 7 yuan, plus 1 yuan per started 20 km beyond 32 km
    Boundary values fall into the higher tier (6000 m -> 4 yuan, etc.).
    """
    meters = _validate_distance(distance)
    for rule in BASIC_FARE_RULES:
        if rule.min_distance_meters <= meters < rule.max_distance_meters:
            return rule.fare_yuan
    extra = meters - EXTENDED_BASE_DISTANCE_METERS
    steps = math.ceil(extra / EXTENDED_STEP_METERS) if extra > 0 else 0
    return EXTENDED_BASE_FARE_YUAN + steps * EXTENDED_STEP_FARE_YUAN


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimate travel time in minutes from distance (meters) and transfers."""
    meters = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    minutes = (
        BOARDING_MINUTES
        + meters / AVERAGE_SPEED_METERS_PER_MINUTE
        + transfer_count * TRANSFER_MINUTES
    )
    return round(minutes, 1)
