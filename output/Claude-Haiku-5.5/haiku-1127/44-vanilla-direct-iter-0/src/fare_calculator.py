"""
Fare calculation for the Beijing Subway.

Fare structure (distance in meters):
    0      <= d < 6000        : 3 yuan
    6000   <= d < 12000       : 4 yuan
    12000  <= d < 22000       : 5 yuan
    22000  <= d < 32000       : 6 yuan
    32000  <= d < 52000       : 7 yuan
    52000  <= d < 72000       : 8 yuan
    ... +1 yuan for every additional 20 km beyond 32 km

Intervals are left-closed and right-open, so a boundary value belongs to the
higher tier. Fractional distances are rounded up to the next whole meter
before the tier is looked up.
"""

import math

BASIC_FARE = 3
PROGRESSIVE_TIERS = (
    (6000, 4),
    (12000, 5),
    (22000, 6),
)
EXTENDED_START_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_METERS = 20000

ESTIMATED_MINUTES_PER_KM = 1.5
ESTIMATED_MINUTES_PER_TRANSFER = 5.0


def _validate_distance(distance):
    """Validate a distance value and return it as a finite float."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("Distance must be a number of meters")
    value = float(distance)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Distance must be a finite number")
    if value < 0:
        raise ValueError("Distance must be non-negative")
    return value


def Sum_money(distance):
    """
    Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters. Fractional values are rounded up
            to the next whole meter (ceiling rounding).

    Returns:
        int: Fare in yuan.

    Raises:
        TypeError: If distance is not a number.
        ValueError: If distance is negative, NaN or infinite.
    """
    value = _validate_distance(distance)
    meters = math.ceil(value)

    if meters < PROGRESSIVE_TIERS[0][0]:
        return BASIC_FARE
    for upper_bound, fare in PROGRESSIVE_TIERS:
        if meters < upper_bound:
            return fare
    # Extended tier: 7 yuan for [32 km, 52 km), 8 yuan for [52 km, 72 km), ...
    extra_steps = (meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS
    return EXTENDED_BASE_FARE + extra_steps


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate the travel time of a journey.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers on the journey.

    Returns:
        float: Estimated travel time in minutes
        (about 1.5 minutes per kilometer plus about 5 minutes per transfer).

    Raises:
        TypeError / ValueError: If the inputs are invalid.
    """
    value = _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int):
        raise TypeError("Transfer count must be an integer")
    if transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    kilometers = value / 1000.0
    return kilometers * ESTIMATED_MINUTES_PER_KM + transfer_count * ESTIMATED_MINUTES_PER_TRANSFER
