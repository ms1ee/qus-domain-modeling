"""Order data model and coordinate validation."""

from typing import Any, Dict, List, Optional, Sequence

import globalvar
from path_planner import MAP_SIZE, Point, manhattan, snap_to_grid

MIN_COORD = 0
MAX_COORD = MAP_SIZE


def validate_coordinate(value: Any, name: str = "coordinate") -> int:
    """Validate that a value is an integer within 0-800.

    Args:
        value: Candidate value.
        name: Label used in error messages.

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if not MIN_COORD <= value <= MAX_COORD:
        raise ValueError(
            f"{name} {value} is out of range ({MIN_COORD}-{MAX_COORD})"
        )
    return value


def validate_point(point: Sequence[Any], label: str) -> Point:
    """Validate an ``(x, y)`` pair of integers in the 0-800 range.

    Args:
        point: Sequence of exactly two values.
        label: Name of the point used in error messages.

    Returns:
        Tuple ``(x, y)`` of validated integers.

    Raises:
        ValueError: If the sequence is malformed or a value is invalid.
    """
    if len(point) != 2:
        raise ValueError(f"{label} point must have exactly 2 coordinates")
    x = validate_coordinate(point[0], f"{label} x")
    y = validate_coordinate(point[1], f"{label} y")
    return x, y


class Order:
    """A food delivery order from a restaurant to a customer.

    Input coordinates are validated and snapped to grid cell centers. The
    order moves through the statuses: created -> assigned -> picking_up ->
    delivering -> completed.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and assign it a unique ID.

        Args:
            res_pos: Restaurant ``(x, y)`` in map units (0-800).
            cus_pos: Customer ``(x, y)`` in map units (0-800).

        Raises:
            ValueError: If coordinates are not integers or out of range.
        """
        self.res_input: Point = validate_point(res_pos, "restaurant")
        self.cus_input: Point = validate_point(cus_pos, "customer")
        self.res_pos: Point = snap_to_grid(*self.res_input)
        self.cus_pos: Point = snap_to_grid(*self.cus_input)

        self.id: int = int(globalvar.get_value("next_order_id", 1))
        globalvar.set_value("next_order_id", self.id + 1)
        self.start_time: int = int(globalvar.get_value("simulated_time", 0))
        self.completion_time: Optional[int] = None
        self.distance: float = 0.0
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None
        self.status: str = "created"
        self.rider_id: Optional[int] = None
        self.route: List[Point] = []

    def assign_to(self, rider_id: int) -> None:
        """Assign this order to a rider by appending it to ``rider.orders``.

        Args:
            rider_id: ID of the rider receiving the order.

        Raises:
            ValueError: If the order is not in the created state or the rider
                does not exist.
        """
        if self.status != "created":
            raise ValueError(f"Order {self.id} is already {self.status}")
        target = None
        for candidate in globalvar.get_value("riders", []):
            if candidate.rider_id == rider_id:
                target = candidate
                break
        if target is None:
            raise ValueError(f"Rider {rider_id} does not exist")
        self.rider_id = rider_id
        self.status = "assigned"
        target.orders.append(self)

    def mark_completed(self, completion_time: int) -> None:
        """Record completion time, time taken and delivery efficiency.

        Efficiency is the direct restaurant-to-customer Manhattan distance
        divided by the total distance the rider travelled for this order.

        Args:
            completion_time: Simulated tick at which delivery finished.
        """
        self.completion_time = completion_time
        self.time_taken = completion_time - self.start_time
        self.status = "completed"
        direct = manhattan(self.res_pos, self.cus_pos)
        self.efficiency = round(direct / self.distance, 3) if self.distance > 0 else 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of this order."""
        return {
            "id": self.id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
            "status": self.status,
            "rider_id": self.rider_id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
        }
