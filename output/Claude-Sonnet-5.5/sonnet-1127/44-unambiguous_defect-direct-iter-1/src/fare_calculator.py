"""Fare and time calculation."""
import math


def Sum_money(distance) -> int:
    """Fare in yuan for a distance in meters."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    d = math.ceil(distance)
    if d < 6000:
        return 3
    if d < 12000:
        return 4
    if d < 22000:
        return 5
    if d < 32000:
        return 6
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated minutes: ~2 min per km plus 5 min per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("negative input")
    return round(distance / 1000.0 * 2.0 + transfer_count * 5.0, 1)
