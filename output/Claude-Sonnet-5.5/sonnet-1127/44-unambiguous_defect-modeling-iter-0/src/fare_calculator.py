"""Beijing subway fare calculation."""

FARE_TIERS = [(0, 6000, 3), (6000, 12000, 4), (12000, 22000, 5), (22000, 32000, 6)]


def Sum_money(distance):
    """Fare in yuan for a distance in meters."""
    if distance is None or distance != distance:
        raise ValueError("invalid distance")
    if distance < 0:
        raise ValueError("distance must be non-negative")
    d = int(round(distance))
    for lo, hi, fare in FARE_TIERS:
        if d < hi:
            return fare
    return 7 + (d - 32000) // 20000


def calculate_estimated_time(distance, transfer_count):
    """Estimated minutes: ~35 km/h average plus 5 min per transfer and 2 min boarding."""
    km = max(distance, 0) / 1000.0
    return km / 35.0 * 60.0 + 5.0 * transfer_count + 2.0
