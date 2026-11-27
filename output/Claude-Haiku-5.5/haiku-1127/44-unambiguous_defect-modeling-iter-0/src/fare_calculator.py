"""
Fare and travel time calculation for Beijing Subway trips.

Fare structure:
  * 0 - under 6 km:        3 yuan
  * 6 km - under 12 km:    4 yuan
  * 12 km - under 22 km:   5 yuan
  * 22 km - under 32 km:   6 yuan
  * 32 km and above:       7 yuan, +1 yuan for every further 20 km

Each lower boundary belongs to the higher tier (e.g. exactly 6000 m costs 4 yuan).
Fractional meters are rounded to the nearest whole meter before lookup.
"""

# (exclusive upper bound in meters, fare in yuan) for the basic and progressive tiers.
FARE_TIERS = (
    (6000, 3),
    (12000, 4),
    (22000, 5),
    (32000, 6),
)
EXTENDED_START_METERS = 32000
EXTENDED_BASE_FARE = 7
EXTENDED_STEP_METERS = 20000

# Average travel speed of the subway in meters per minute (35 km/h).
AVERAGE_SPEED_M_PER_MIN = 35000.0 / 60.0
# Fixed boarding/alighting allowance per trip, in minutes.
BOARDING_MINUTES = 2.0
# Extra time per transfer (walking and waiting), in minutes.
TRANSFER_MINUTES = 4.0


def Sum_money(distance):
    """
    Calculate the subway fare for a travel distance.

    Args:
        distance: Travel distance in meters (int or float).

    Returns:
        int: Fare in yuan.

    Raises:
        ValueError: If the distance is negative or not a finite number.
    """
    try:
        meters = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid distance: {distance!r}") from exc
    if meters != meters or meters in (float("inf"), float("-inf")):
        raise ValueError("Distance must be a finite number")
    if meters < 0:
        raise ValueError("Distance must not be negative")

    meters = int(round(meters))
    for upper, fare in FARE_TIERS:
        if meters < upper:
            return fare
    # Extended tier: fare rises by 1 yuan for each full 20 km beyond 32 km.
    return EXTENDED_BASE_FARE + int((meters - EXTENDED_START_METERS) // EXTENDED_STEP_METERS)


def calculate_estimated_time(distance, transfer_count):
    """
    Estimate the travel time of a trip.

    Args:
        distance: Travel distance in meters.
        transfer_count: Number of transfers on the trip.

    Returns:
        float: Estimated travel time in minutes.

    Raises:
        ValueError: If the distance or transfer count is invalid.
    """
    meters = float(distance)
    if meters < 0:
        raise ValueError("Distance must not be negative")
    if transfer_count < 0:
        raise ValueError("Transfer count must not be negative")
    riding = meters / AVERAGE_SPEED_M_PER_MIN
    return riding + BOARDING_MINUTES + TRANSFER_MINUTES * transfer_count
