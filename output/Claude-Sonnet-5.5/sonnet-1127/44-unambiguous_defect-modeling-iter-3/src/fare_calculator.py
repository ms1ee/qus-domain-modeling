"""Fare and time estimation."""

FARE_TIERS = [(0, 6000, 3), (6000, 12000, 4), (12000, 22000, 5), (22000, 32000, 6)]


def Sum_money(distance) -> int:
    """Fare in yuan for a distance in meters."""
    if distance is None or distance < 0:
        raise ValueError("Distance must be non-negative")
    d = int(round(distance))
    for lo, hi, fare in FARE_TIERS:
        if d < hi:
            return fare
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count) -> float:
    """Estimated minutes: ~35 km/h average, plus 5 min per transfer, 2 min boarding."""
    return round(distance / 1000.0 / 35.0 * 60.0 + 5.0 * transfer_count + 2.0, 1)


class FareCalculator:
    def calculate(self, distance):
        return Sum_money(distance)
