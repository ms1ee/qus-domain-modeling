"""Order data model: coordinate validation, cell-centre conversion and lifecycle."""

import math
from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import MAP_SIZE, PathPlanner

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_COMPLETED = "completed"


def validate_point(point: Sequence[int], label: str) -> Tuple[int, int]:
    """Validate an input ``[x, y]`` pair.

    Args:
        point: Sequence with exactly two integer coordinates.
        label: Human readable name used in error messages.

    Returns:
        The validated ``(x, y)`` tuple.

    Raises:
        ValueError: If the shape, type or range of the coordinates is invalid.
    """
    try:
        items = list(point)
    except TypeError as exc:
        raise ValueError(f"{label} location must be a pair of integers") from exc
    if len(items) != 2:
        raise ValueError(f"{label} location must contain exactly 2 values")
    for value in items:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers, got {value!r}")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"{label} coordinates must be within 0-{MAP_SIZE}, got {value}"
            )
    return items[0], items[1]


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier (starts at 1).
        status: One of "pending", "assigned", "picked_up", "completed".
        raw_res_pos: Restaurant coordinates as entered by the user.
        raw_cus_pos: Customer coordinates as entered by the user.
        res_pos: Restaurant grid-cell centre ``(x, y)``.
        cus_pos: Customer grid-cell centre ``(x, y)``.
        rider_id: ID of the assigned rider, or None.
        start_time: Tick at which the order was created.
        pickup_time: Tick at which the rider reached the restaurant.
        complete_time: Tick at which the order was delivered.
        distance: Street (Manhattan) distance between restaurant and customer.
        time_taken: Ticks from creation to delivery.
        efficiency: Distance covered per tick over the whole order.
    """

    _id_counter = 0

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and convert its coordinates to cell centres.

        Args:
            res_pos: Restaurant coordinates ``[x, y]`` in the range 0-800.
            cus_pos: Customer coordinates ``[x, y]`` in the range 0-800.

        Raises:
            ValueError: If a coordinate is not an integer or is out of range.
        """
        raw_res = validate_point(res_pos, "restaurant")
        raw_cus = validate_point(cus_pos, "customer")

        Order._id_counter += 1
        self.id: int = Order._id_counter
        self.raw_res_pos: Tuple[int, int] = raw_res
        self.raw_cus_pos: Tuple[int, int] = raw_cus
        self.res_pos: Tuple[int, int] = (
            PathPlanner.cell_center(raw_res[0]),
            PathPlanner.cell_center(raw_res[1]),
        )
        self.cus_pos: Tuple[int, int] = (
            PathPlanner.cell_center(raw_cus[0]),
            PathPlanner.cell_center(raw_cus[1]),
        )
        self.status: str = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("time", 0) or 0)
        self.pickup_time: Optional[int] = None
        self.complete_time: Optional[int] = None
        self.distance: int = abs(self.res_pos[0] - self.cus_pos[0]) + abs(
            self.res_pos[1] - self.cus_pos[1]
        )
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def assign_to(self, rider_id: int) -> None:
        """Mark the order as assigned to the rider with the given ID.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self, tick: int) -> None:
        """Record that the rider reached the restaurant.

        Args:
            tick: Simulation tick of the pickup.
        """
        self.pickup_time = tick
        self.status = STATUS_PICKED_UP

    def complete(self, tick: int) -> None:
        """Mark the order delivered and record completion statistics.

        Args:
            tick: Simulation tick of the delivery.
        """
        self.complete_time = tick
        self.status = STATUS_COMPLETED
        self.time_taken = max(0, tick - self.start_time)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 3)
        else:
            self.efficiency = float(self.distance)

    def is_active(self) -> bool:
        """Return True while the order has not been completed."""
        return self.status != STATUS_COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
