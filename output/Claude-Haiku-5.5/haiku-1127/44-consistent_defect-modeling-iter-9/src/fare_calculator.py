"""Fare and travel-time calculation for Beijing Subway trips."""

import math

from models import FareCalculationError

MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0

# Fare tier thresholds in meters (after ceiling rounding of the distance).
BASIC_FARE_LIMIT_M = 6000        # up to 6 km: 3 yuan (6 km itself is 3 yuan)
SECOND_FARE_LIMIT_M = 12000      # up to 12 km: 4 yuan
THIRD_FARE_LIMIT_M = 22000       # below 22 km: 5 yuan; 22 km itself enters the 6 yuan tier
FOURTH_FARE_LIMIT_M = 32000      # up to 32 km: 6 yuan
EXTENDED_STEP_M = 20000          # beyond 32 km: +1 yuan per 20 km


def Sum_money(distance):
    """Return the fare in yuan for a trip of the given distance in meters.

    Rules:
      * distance is rounded up to the next whole meter (ceiling rounding);
      * <= 6000 m: 3 yuan;  <= 12000 m: 4 yuan;  < 22000 m: 5 yuan;
      * 22000 m .. 32000 m (inclusive): 6 yuan;
      * > 32000 m: 6 yuan plus 1 yuan for every started 20 km
        (32-52 km: 7 yuan, 52-72 km: 8 yuan, ...).

    Raises:
        FareCalculationError: if the distance is not a finite non-negative number.
    """
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Invalid distance: {distance!r}") from exc
    if math.isnan(value) or math.isinf(value) or value < 0:
        raise FareCalculationError(f"Distance must be a finite non-negative number, got {distance!r}")

    meters = math.ceil(value)
    if meters <= BASIC_FARE_LIMIT_M:
        return 3
    if meters <= SECOND_FARE_LIMIT_M:
        return 4
    if meters < THIRD_FARE_LIMIT_M:
        return 5
    if meters <= FOURTH_FARE_LIMIT_M:
        return 6
    return 6 + math.ceil((meters - FOURTH_FARE_LIMIT_M) / EXTENDED_STEP_M)


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfer count.

    Uses about 1.5 minutes per kilometer plus about 5 minutes per transfer.
    """
    if distance < 0:
        raise ValueError("distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return (float(distance) / 1000.0) * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
