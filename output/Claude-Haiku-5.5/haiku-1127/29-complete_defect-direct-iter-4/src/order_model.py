"""Order data model with coordinate normalisation and lifecycle tracking.

Order lifecycle statuses: "pending" -> "assigned" -> "picked_up" -> "completed".
"""

from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import GRID_SIZE, cell_center, grid_cell, manhattan

Point = Tuple[int, int]


def validate_point(point: Sequence[int], label: str = "point") -> Point:
    """Validate an integer coordinate pair within the 0-800 range.

    Args:
        point: Sequence of two integers (x, y).
        label: Name used in error messages.

    Returns:
        The validated (x, y) tuple.

    Raises:
        ValueError: If the point is malformed, not integral, or out of range.
    """
    try:
        x, y = point
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a pair of coordinates") from exc
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers")
        if not 0 <= value <= GRID_SIZE:
            raise ValueError(f"{label} coordinate {value} is outside 0-{GRID_SIZE}")
    return (x, y)


class Order:
    """A food delivery order from a restaurant to a customer."""

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and convert its locations to grid cell centers.

        Args:
            res_pos: Restaurant coordinates (x, y), range 0-800.
            cus_pos: Customer coordinates (x, y), range 0-800.

        Raises:
            ValueError: If either coordinate pair is invalid.
        """
        raw_res = validate_point(res_pos, "restaurant")
        raw_cus = validate_point(cus_pos, "customer")
        counter = int(globalvar.get_value("order_counter", 0) or 0) + 1
        globalvar.set_value("order_counter", counter)

        self.id: int = counter
        self.raw_res_pos: Point = raw_res
        self.raw_cus_pos: Point = raw_cus
        self.res_pos: Point = (cell_center(raw_res[0]), cell_center(raw_res[1]))
        self.cus_pos: Point = (cell_center(raw_cus[0]), cell_center(raw_cus[1]))
        self.status: str = "pending"
        self.rider_id: Optional[int] = None
        self.start_tick: int = self._now()
        self.assigned_tick: Optional[int] = None
        self.pickup_tick: Optional[int] = None
        self.completed_tick: Optional[int] = None
        self.time_taken: Optional[int] = None
        self.distance: int = manhattan(self.res_pos, self.cus_pos)
        config = globalvar.get_value("config") or {}
        divisor = int(config.get("distance_fee_divisor", 10))
        base_fee = int(config.get("base_delivery_fee", 100))
        self.reward: int = base_fee + self.distance // max(divisor, 1)

    @staticmethod
    def _now() -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("time", 0) or 0)

    @property
    def restaurant_cell(self) -> Point:
        """Zero-based grid cell of the restaurant."""
        return grid_cell(self.res_pos)

    @property
    def customer_cell(self) -> Point:
        """Zero-based grid cell of the customer."""
        return grid_cell(self.cus_pos)

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to a rider.

        The caller is responsible for appending the order to the rider's
        ``orders`` list.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = int(rider_id)
        self.status = "assigned"
        self.assigned_tick = self._now()

    def mark_picked_up(self, tick: int) -> None:
        """Record arrival at the restaurant.

        Args:
            tick: Simulated tick of the pickup.
        """
        self.status = "picked_up"
        self.pickup_tick = tick

    def complete(self, tick: int) -> int:
        """Mark the order as delivered and record efficiency data.

        Args:
            tick: Simulated tick of the delivery.

        Returns:
            The delivery fee earned for this order.
        """
        self.status = "completed"
        self.completed_tick = tick
        self.time_taken = tick - self.start_tick
        return self.reward

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable description of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "distance": self.distance,
            "reward": self.reward,
            "start_tick": self.start_tick,
            "assigned_tick": self.assigned_tick,
            "pickup_tick": self.pickup_tick,
            "completed_tick": self.completed_tick,
            "time_taken": self.time_taken,
        }
