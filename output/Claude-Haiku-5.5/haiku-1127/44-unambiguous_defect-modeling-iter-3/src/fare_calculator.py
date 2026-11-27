"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distance in meters):
  0 - 6 km        : 3 yuan
  6 - 12 km       : 4 yuan
  12 - 22 km      : 5 yuan
  22 - 32 km      : 6 yuan
  over 32 km      : 7 yuan, plus 1 yuan for every further (or partial) 20 km
"""

import math
from dataclasses import dataclass

from models import FareError


@dataclass(frozen=True)
class FareRule:
    """Maps a half-open distance interval [min_distance, max_distance) to a fare."""

    min_distance_m: float
    max_distance_m: float
    fare: int


# Basic and progressive tiers, ordered by distance.
FARE_RULES = (
    FareRule(0.0, 6000.0, 3),
    FareRule(6000.0, 12000.0, 4),
    FareRule(12000.0, 22000.0, 5),
    FareRule(22000.0, 32000.0, 6),
)

# Extended tier parameters.
EXTENDED_START_M = 32000.0
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_M = 20000.0

# Travel-time model parameters.
AVERAGE_SPEED_KMH = 35.0      # average operating speed including dwell time
TRANSFER_TIME_MIN = 5.0       # walking and waiting time per transfer
BOARDING_TIME_MIN = 2.0       # initial boarding time


def Sum_money(distance):
    """Return the fare in yuan for a trip of ``distance`` meters.

    Boundaries belong to the upper tier: 6000 m -> 4 yuan, 12000 m -> 5 yuan,
    22000 m -> 6 yuan, 32000 m -> 7 yuan. Distances beyond 32 km are rounded
    up to the next 20 km step.
    """
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise FareError(f"Invalid distance: {distance!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise FareError(f"Invalid distance: {distance!r}")
    if value < 0:
        raise FareError("Distance cannot be negative")

    for rule in FARE_RULES:
        if rule.min_distance_m <= value < rule.max_distance_m:
            return rule.fare

    # Extended tier: rounded up in 20 km steps beyond 32 km.
    extra_steps = math.ceil((value - EXTENDED_START_M) / EXTENDED_STEP_M)
    return EXTENDED_BASE_FARE + extra_steps


def calculate_estimated_time(distance, transfer_count):
    """Return an estimated travel time in minutes for ``distance`` meters and transfers."""
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    if transfer_count < 0:
        raise ValueError("Transfer count cannot be negative")
    if distance == 0 and transfer_count == 0:
        return 0.0
    travel_minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = travel_minutes + BOARDING_TIME_MIN + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
