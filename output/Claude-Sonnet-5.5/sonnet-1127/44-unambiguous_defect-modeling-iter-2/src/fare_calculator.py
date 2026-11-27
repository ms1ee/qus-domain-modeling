"""Fare and time estimation."""

FARE_TIERS = [(0, 6000, 3), (6000, 12000, 4), (12000, 22000, 5), (22000, 32000, 6)]


def Sum_money(distance) -> int:
    """Fare in yuan for a distance in meters."""
    if distance is None or distance < 0:
        raise ValueError("Distance must be a non-negative number")
    d = int(round(distance))
    for lo, hi, fare in FARE_TIERS:
        if lo <= d < hi:
            return fare
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated minutes: ~35 km/h average, +2 min boarding, +5 min per transfer."""
    if distance < 0 or transfer_count < 0:
        raise ValueError("Invalid distance or transfer count")
    return round(distance / 1000.0 / 35.0 * 60.0 + 2 + 5 * transfer_count, 1)


class FareCalculator:
    def calculate(self, distance):
        return Sum_money(distance)
