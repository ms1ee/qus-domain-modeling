"""Fare and time calculation."""
import math


def Sum_money(distance):
    """Fare in yuan for a distance in meters."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    d = math.ceil(distance - 1e-9)
    if d < 6000:
        return 3
    if d < 12000:
        return 4
    if d < 22000:
        return 5
    if d < 32000:
        return 6
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: 35 km/h average speed plus 5 min per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("negative input")
    return distance / 1000.0 / 35.0 * 60.0 + 5.0 * transfer_count + 2.0
