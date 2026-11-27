"""
Fare calculation according to the Beijing Subway fare structure.

- 0-6 km: 3 yuan
- 6-12 km: 4 yuan
- 12-22 km: 5 yuan
- 22-32 km: 6 yuan
- beyond 32 km: +1 yuan for every additional 20 km (or part thereof)

Fractional kilometers are rounded up before tier lookup.
"""

import math

# (upper bound in km inclusive, fare in yuan)
FARE_TABLE = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_STEP_KM = 20

AVERAGE_SPEED_KMH = 35.0       # average operating speed including dwell time
TRANSFER_TIME_MINUTES = 5.0    # average time per transfer


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError("distance must be a number (meters)")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("distance must be a finite number")
    if distance < 0:
        raise ValueError("distance cannot be negative")


def distance_to_km(distance):
    """Convert meters to whole kilometers, rounding up."""
    _validate_distance(distance)
    return int(math.ceil(distance / 1000.0 - 1e-9)) if distance > 0 else 0


def Sum_money(distance):
    """Return the fare (yuan) for a trip of ``distance`` meters."""
    km = distance_to_km(distance)
    for upper, fare in FARE_TABLE:
        if km <= upper:
            return fare
    extra = km - EXTENDED_BASE_KM
    return EXTENDED_BASE_FARE + int(math.ceil(extra / EXTENDED_STEP_KM))


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for ``distance`` meters and transfers."""
    _validate_distance(distance)
    if transfer_count is None:
        transfer_count = 0
    if transfer_count < 0:
        raise ValueError("transfer_count cannot be negative")
    riding = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0
    return round(float(riding + transfer_count * TRANSFER_TIME_MINUTES), 1)
