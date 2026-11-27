"""Fare calculation for Beijing Subway."""

FARE_TIERS = {"0-6km": 3, "6-12km": 4, "12-22km": 5, "22-32km": 6, "32km+": 7}


def Sum_money(distance):
    """Fare in yuan for a distance in meters."""
    if distance is None or distance < 0:
        raise ValueError("distance must be non-negative")
    d = int(round(distance))
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
    """Estimated minutes: ~35 km/h running speed plus 5 min per transfer."""
    return distance / 1000.0 / 35.0 * 60.0 + 5.0 * transfer_count


class FareCalculator:
    def __init__(self):
        self.fare_tiers = dict(FARE_TIERS)

    def calculate(self, distance):
        return Sum_money(distance)
