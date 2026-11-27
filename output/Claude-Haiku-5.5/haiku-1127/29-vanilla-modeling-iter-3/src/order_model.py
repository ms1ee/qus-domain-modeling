"""Order data model with coordinate normalisation and lifecycle tracking."""

from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from config import MAP_SIZE
from path_planner import Point, to_cell_center

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _validate_point(point: Sequence[Any], label: str) -> Point:
    """Validate an ``(x, y)`` pair of integers within the map range.

    Args:
        point: Two-element sequence.
        label: Name used in error messages.

    Returns:
        The validated point as a tuple of ints.

    Raises:
        ValueError: If the shape, type or range is invalid.
    """
    try:
        x, y = point
    except (TypeError, ValueError):
        raise ValueError(f"{label} location must be a pair of integers")
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinates must be integers")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"{label} coordinate {value} out of range 0-{MAP_SIZE}")
    return (x, y)


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier (auto-incremented).
        res_pos: Restaurant cell-centre coordinates.
        cus_pos: Customer cell-centre coordinates.
        status: One of pending, assigned, picking_up, delivering, completed.
        rider_id: Identifier of the assigned rider or ``None``.
        start_time: Tick at which the order was created.
        completion_time: Tick at which the order was delivered or ``None``.
        distance: Total distance travelled by the rider for this order.
        time_taken: Ticks between creation and completion or ``None``.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and convert both locations to grid cell centres.

        Args:
            res_pos: Restaurant ``(x, y)`` in the range 0-800.
            cus_pos: Customer ``(x, y)`` in the range 0-800.

        Raises:
            ValueError: If a coordinate is not an integer or out of range.
        """
        restaurant = _validate_point(res_pos, "restaurant")
        customer = _validate_point(cus_pos, "customer")
        counter = int(globalvar.get_value("order_id_counter") or 0) + 1
        globalvar.set_value("order_id_counter", counter)

        self.id = counter
        self.res_pos: Point = to_cell_center(restaurant)
        self.cus_pos: Point = to_cell_center(customer)
        self.status = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_time = int(globalvar.get_value("current_tick") or 0)
        self.completion_time: Optional[int] = None
        self.distance = 0.0
        self.time_taken: Optional[int] = None

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been assigned to ``rider_id``.

        The caller is responsible for appending the order to ``rider.orders``.

        Args:
            rider_id: Identifier of the chosen rider.
        """
        self.rider_id = int(rider_id)
        self.status = STATUS_ASSIGNED

    def set_status(self, status: str) -> None:
        """Update the lifecycle status string."""
        self.status = status

    def add_distance(self, units: float) -> None:
        """Accumulate travelled distance for this order."""
        self.distance += units

    def mark_completed(self, tick: int) -> None:
        """Mark the order delivered and record completion metrics.

        Args:
            tick: Simulation tick at which delivery finished.
        """
        self.completion_time = tick
        self.time_taken = max(tick - self.start_time, 0)
        self.status = STATUS_COMPLETED

    def is_completed(self) -> bool:
        """Return True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    @property
    def efficiency(self) -> Optional[float]:
        """Average distance per tick for a completed order, or ``None``."""
        if not self.time_taken:
            return None
        return self.distance / self.time_taken

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the order."""
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
