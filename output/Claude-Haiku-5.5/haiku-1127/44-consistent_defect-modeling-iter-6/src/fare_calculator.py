"""
Fare calculation for the Beijing Subway.

Fare structure (distances in meters):
    * Basic tier:      up to 6 km          -> 3 yuan
    * Progressive tier: 6 km to 12 km       -> 4 yuan
                        12 km to 22 km      -> 5 yuan
                        22 km to 32 km      -> 6 yuan
    * Extended tier:   over 32 km          -> 6 yuan + 1 yuan per 20 km (or part thereof)
                        e.g. 32-52 km: 7 yuan, 52-72 km: 8 yuan

Boundary handling follows the explicit examples in the PRD:
    6000 m -> 3 yuan, 12000 m -> 4 yuan, 22000 m -> 6 yuan, 32000 m -> 6 yuan.
Fractional distances are rounded up to the next whole meter before pricing.
"""

import math

# Distances (meters) at which the progressive tiers end.
TIER_BASIC_END_M = 6000
TIER_SECOND_END_M = 12000
TIER_THIRD_END_M = 22000
TIER_FOURTH_END_M = 32000

# Extended tier step length in meters (one additional yuan per step).
EXTENSION_STEP_M = 20000

# Estimated time model.
MINUTES_PER_KM = 1.5
MINUTES_PER_TRANSFER = 5.0


def Sum_money(distance: float) -> int:
    """Calculate the subway fare for a travelled distance.

    Args:
        distance: Travelled distance in meters. Fractional values are
            rounded up to the next whole meter.

    Returns:
        Fare in yuan (integer).

    Raises:
        ValueError: If the distance is negative or not finite.
    """
    if not math.isfinite(distance):
        raise ValueError("Distance must be a finite number")
    if distance < 0:
        raise ValueError("Distance must be non-negative")

    meters = math.ceil(distance)

    if meters <= TIER_BASIC_END_M:
        return 3
    if meters <= TIER_SECOND_END_M:
        return 4
    if meters < TIER_THIRD_END_M:
        return 5
    if meters <= TIER_FOURTH_END_M:
        return 6

    # Extended tier: each started 20 km beyond 32 km adds one yuan.
    extra_steps = math.ceil((meters - TIER_FOURTH_END_M) / EXTENSION_STEP_M)
    return 6 + extra_steps


def calculate_estimated_time(distance: float, transfer_count: int) -> float:
    """Estimate travel time in minutes.

    Uses roughly 1.5 minutes per kilometre plus roughly 5 minutes per transfer.

    Args:
        distance: Travelled distance in meters.
        transfer_count: Number of transfers.

    Returns:
        Estimated travel time in minutes.
    """
    if distance < 0:
        raise ValueError("Distance must be non-negative")
    if transfer_count < 0:
        raise ValueError("Transfer count must be non-negative")
    kilometres = distance / 1000.0
    return kilometres * MINUTES_PER_KM + transfer_count * MINUTES_PER_TRANSFER
