"""Fare and travel-time calculation for the Beijing Subway.

Fare structure (distance in meters):
    0      - <6000      : 3 yuan
    6000   - <12000     : 4 yuan
    12000  - <22000     : 5 yuan
    22000  - <32000     : 6 yuan
    >=32000            : 7 yuan, plus 1 yuan for every further 20 km
Boundary values belong to the higher tier (e.g. exactly 6000 m costs 4 yuan).
Fractional distances are resolved by flooring within the extended tier.
"""
import math
import numbers
from dataclasses import dataclass

from errors import FareCalculationError

AVERAGE_SPEED_KMH = 35.0        # average commercial operating speed
BOARDING_OVERHEAD_MIN = 3.0     # waiting / boarding allowance per trip
TRANSFER_TIME_MIN = 5.0         # walking and waiting time per transfer


@dataclass(frozen=True)
class FareRule:
    """One fare tier.

    Attributes:
        min_distance_m: inclusive lower bound of the tier in meters.
        max_distance_m: exclusive upper bound in meters, or None if open-ended.
        base_fare: fare in yuan at the lower bound of the tier.
        increment_distance_m: distance per additional fare step (0 = none).
        increment_fare: yuan added per increment step.
    """

    min_distance_m: float
    max_distance_m: object
    base_fare: int
    increment_distance_m: float
    increment_fare: int


FARE_RULES = (
    FareRule(0.0, 6000.0, 3, 0.0, 0),
    FareRule(6000.0, 12000.0, 4, 0.0, 0),
    FareRule(12000.0, 22000.0, 5, 0.0, 0),
    FareRule(22000.0, 32000.0, 6, 0.0, 0),
    FareRule(32000.0, None, 7, 20000.0, 1),
)


def _validate_distance(distance):
    """Validate a distance in meters and return it as float."""
    if isinstance(distance, bool) or not isinstance(distance, numbers.Real):
        raise FareCalculationError("distance must be a number of meters")
    value = float(distance)
    if math.isnan(value) or math.isinf(value):
        raise FareCalculationError("distance must be a finite number")
    if value < 0:
        raise FareCalculationError("distance must not be negative")
    return value


def Sum_money(distance):
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: travelled distance in meters.

    Returns:
        Fare in yuan (int).

    Raises:
        FareCalculationError: if the distance is invalid.
    """
    meters = _validate_distance(distance)
    for rule in FARE_RULES:
        if rule.max_distance_m is None or meters < rule.max_distance_m:
            if rule.increment_distance_m > 0:
                steps = int((meters - rule.min_distance_m) // rule.increment_distance_m)
                return rule.base_fare + steps * rule.increment_fare
            return rule.base_fare
    raise FareCalculationError("no fare rule matches distance {}".format(distance))


def calculate_estimated_time(distance, transfer_count):
    """Estimate the travel time of a trip in minutes.

    The estimate combines riding time at an average speed, a fixed boarding
    allowance, and a penalty per transfer.

    Args:
        distance: travelled distance in meters.
        transfer_count: number of line transfers.

    Returns:
        Estimated time in minutes (float, one decimal place).

    Raises:
        FareCalculationError: on invalid input.
    """
    meters = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise FareCalculationError("transfer_count must be an integer")
    if transfer_count < 0:
        raise FareCalculationError("transfer_count must not be negative")
    riding_min = (meters / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    total = BOARDING_OVERHEAD_MIN + riding_min + transfer_count * TRANSFER_TIME_MIN
    return round(total, 1)
