"""Fare and time estimation."""


def Sum_money(distance):
    """Fare in yuan for a distance in meters."""
    d = int(round(float(distance)))
    if d < 0:
        raise ValueError("distance cannot be negative")
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
    """Estimated minutes: ~2.5 min/km plus 5 min per transfer."""
    return round(distance / 1000.0 * 2.5 + transfer_count * 5.0, 1)
