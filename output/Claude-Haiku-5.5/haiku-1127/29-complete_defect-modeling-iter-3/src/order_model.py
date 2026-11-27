"""Order data model.

An order stores the raw restaurant and customer positions entered by the
user (0-800) and the grid cell centres used for movement.
"""

import itertools
from typing import Any, Dict, Tuple

from path_planner import MAP_SIZE, PathPlanner, manhattan

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

Point = Tuple[int, int]

_ORDER_IDS = itertools.count(1)


def validate_point(pos: Any, label: str) -> Point:
    """Validate an ``(x, y)`` coordinate pair.

    Args:
        pos: Object expected to contain two integers.
        label: Human-readable name used in error messages.

    Returns:
        The validated point as a tuple.

    Raises:
        ValueError: If the pair is malformed, not integer, or out of range.
    """
    try:
        x, y = pos
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} position must contain exactly two integers") from exc
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} coordinate {value!r} is not an integer")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"{label} coordinate {value} is out of range 0-{MAP_SIZE}"
            )
    return (x, y)


class Order:
    """A food delivery order from a restaurant to a customer."""

    def __init__(self, res_pos, cus_pos) -> None:
        """Create a pending order.

        Args:
            res_pos: Restaurant position ``[x, y]`` in range 0-800.
            cus_pos: Customer position ``[x, y]`` in range 0-800.

        Raises:
            ValueError: If either position is invalid.
        """
        self.id: int = next(_ORDER_IDS)
        self.res_pos: Point = validate_point(res_pos, "Restaurant")
        self.cus_pos: Point = validate_point(cus_pos, "Customer")
        self.res_center: Point = PathPlanner.cell_center_point(self.res_pos)
        self.cus_center: Point = PathPlanner.cell_center_point(self.cus_pos)
        self.status: str = STATUS_PENDING
        self.rider_id = None
        self.start_time: int = 0
        self.completion_time = None
        self.distance: int = manhattan(self.res_center, self.cus_center)
        self.time_taken = None

    def assign_to(self, rider_id: int) -> None:
        """Record that the order is assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.

        Raises:
            ValueError: If the order is not pending.
        """
        if self.status != STATUS_PENDING:
            raise ValueError(f"Order {self.id} cannot be assigned in status {self.status}")
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def complete(self, tick: int) -> None:
        """Mark the order as delivered and record completion data.

        Args:
            tick: Simulated tick at which delivery finished.
        """
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        self.status = STATUS_COMPLETED

    @property
    def efficiency(self) -> float:
        """Distance covered per tick for a completed order (0.0 if unknown)."""
        if not self.time_taken:
            return 0.0
        return round(self.distance / self.time_taken, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }
