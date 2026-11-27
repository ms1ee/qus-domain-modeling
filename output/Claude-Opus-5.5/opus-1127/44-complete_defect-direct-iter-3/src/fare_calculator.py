"""Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometres):
    0-6 km   : 3 yuan
    6-12 km  : 4 yuan
    12-22 km : 5 yuan
    22-32 km : 6 yuan
    > 32 km  : +1 yuan for every additional 20 km (or part thereof)
"""

import math

# (upper bound in km inclusive, fare in yuan)
FARE_TIERS = [
    (6, 3),
    (12, 4),
    (22, 5),
    (32, 6),
]
EXTENDED_STEP_KM = 20
AVERAGE_SPEED_KMH = 35.0
TRANSFER_TIME_MINUTES = 5.0


def Sum_money(distance):
    """Return the fare (yuan) for a distance given in meters."""
    if distance is None:
        raise ValueError("Distance cannot be None")
    try:
        distance = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid distance: {distance!r}") from exc
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError(f"Invalid distance: {distance!r}")
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    km = math.ceil(distance / 1000.0)
    for upper, fare in FARE_TIERS:
        if km <= upper:
            return fare
    last_upper, last_fare = FARE_TIERS[-1]
    return last_fare + math.ceil((km - last_upper) / EXTENDED_STEP_KM)


def calculate_estimated_time(distance, transfer_count):
    """Estimate travel time in minutes from distance (meters) and transfers."""
    if distance is None or distance < 0:
        raise ValueError("Distance must be non-negative")
    if transfer_count is None or transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    ride = distance / 1000.0 / AVERAGE_SPEED_KMH * 60.0
    return round(ride + transfer_count * TRANSFER_TIME_MINUTES, 1)
