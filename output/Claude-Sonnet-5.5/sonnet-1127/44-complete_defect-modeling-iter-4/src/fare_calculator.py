"""Fare calculation."""
import math

FARE_RULES = [(6, 3), (12, 4), (22, 5), (32, 6)]


def Sum_money(distance) -> int:
    """Fare in yuan for a distance in meters (km rounded up)."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    km = math.ceil(distance / 1000.0)
    for limit, fare in FARE_RULES:
        if km <= limit:
            return fare
    return 6 + int(math.ceil((km - 32) / 20.0))


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated minutes: 35 km/h average plus 5 minutes per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("invalid arguments")
    return round(distance / 1000.0 / 35.0 * 60.0 + transfer_count * 5.0, 1)
