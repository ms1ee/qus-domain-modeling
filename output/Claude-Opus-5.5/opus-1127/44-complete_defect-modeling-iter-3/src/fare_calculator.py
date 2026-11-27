"""Beijing Subway fare calculation.

Fare structure (distance rounded up to whole kilometers):
  * 0 - 6 km   : 3 yuan
  * 6 - 12 km  : 4 yuan
  * 12 - 22 km : 5 yuan
  * 22 - 32 km : 6 yuan
  * over 32 km : +1 yuan for every (started) 20 km
"""

import math

from models import Fare, FareTier

FARE_TIERS = [
    FareTier(0, 6, 3),
    FareTier(6, 12, 4),
    FareTier(12, 22, 5),
    FareTier(22, 32, 6),
]
EXTENDED_BASE_KM = 32
EXTENDED_BASE_FARE = 6
EXTENDED_INCREMENT_KM = 20
EXTENDED_INCREMENT_FARE = 1

# Fare structure as a dictionary: (min_km, max_km) -> fare
FARE_STRUCTURE = {(t.min_distance_km, t.max_distance_km): t.fare for t in FARE_TIERS}

AVERAGE_SPEED_KMH = 35.0     # average operating speed including stops
TRANSFER_TIME_MINUTES = 5.0  # average time per transfer


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise TypeError(f"Distance must be a number (meters), got {type(distance).__name__}")
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance cannot be negative")


def distance_to_km(distance):
    """Convert meters to kilometers, rounding fractional kilometers up."""
    _validate_distance(distance)
    if isinstance(distance, int):
        return -(-distance // 1000)
    return int(math.ceil(distance / 1000.0))


def Sum_money(distance):
    """Return the fare in yuan for a trip of ``distance`` meters."""
    km = distance_to_km(distance)
    for tier in FARE_TIERS:
        if km <= tier.max_distance_km:
            return tier.fare
    extra = km - EXTENDED_BASE_KM
    increments = -(-extra // EXTENDED_INCREMENT_KM)
    return EXTENDED_BASE_FARE + increments * EXTENDED_INCREMENT_FARE


def calculate_fare(distance):
    """Return a ``Fare`` object for ``distance`` meters."""
    return Fare(amount=Sum_money(distance), distance_km=round(distance / 1000.0, 3))


def calculate_estimated_time(distance, transfer_count):
    """Estimated travel time in minutes for ``distance`` meters and transfers."""
    _validate_distance(distance)
    if isinstance(transfer_count, bool) or not isinstance(transfer_count, int) or transfer_count < 0:
        raise ValueError("transfer_count must be a non-negative integer")
    minutes = (distance / 1000.0) / AVERAGE_SPEED_KMH * 60.0 + transfer_count * TRANSFER_TIME_MINUTES
    return float(round(minutes, 1))
