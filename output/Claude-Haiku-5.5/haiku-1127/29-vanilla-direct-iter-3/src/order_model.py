"""Order data model.

An order is created from raw coordinates in the range 0-800. Each coordinate
pair is converted to the centre point of its grid cell.
"""

from typing import Any, Dict, Optional, Sequence, Tuple

import globalvar
from path_planner import PathPlanner, path_length

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = 8

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def validate_coordinate(value: Any, name: str = "coordinate") -> int:
    """Validate that ``value`` is an integer in the range 0-800.

    Args:
        value: Value to validate.
        name: Human-readable name used in error messages.

    Returns:
        The validated integer.

    Raises:
        TypeError: If ``value`` is not an integer.
        ValueError: If ``value`` is outside 0-800.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {value!r}")
    if not 0 <= value <= MAP_SIZE:
        raise ValueError(
            f"{name} must be between 0 and {MAP_SIZE}, got {value}")
    return value


def to_grid_center(x: int, y: int) -> Tuple[int, int]:
    """Convert a map coordinate to the centre of its 100x100 grid cell.

    Uses ``center = (coord // 100) * 100 + 50``. The value 800 belongs to the
    last cell, so it is clamped to that cell.

    Args:
        x: X coordinate (0-800).
        y: Y coordinate (0-800).

    Returns:
        ``(center_x, center_y)``.
    """
    x = validate_coordinate(x, "x")
    y = validate_coordinate(y, "y")
    cell_x = min(x // CELL_SIZE, GRID_CELLS - 1)
    cell_y = min(y // CELL_SIZE, GRID_CELLS - 1)
    return cell_x * CELL_SIZE + CELL_SIZE // 2, \
        cell_y * CELL_SIZE + CELL_SIZE // 2


def _split_position(pos: Sequence[Any], name: str) -> Tuple[int, int]:
    """Split a position sequence into validated ``(x, y)`` integers."""
    if len(pos) != 2:
        raise ValueError(f"{name} must contain exactly two coordinates")
    return (validate_coordinate(pos[0], f"{name} x"),
            validate_coordinate(pos[1], f"{name} y"))


class Order:
    """A food delivery order.

    Attributes:
        id: Unique order identifier.
        raw_res: Restaurant coordinates as entered by the user.
        raw_cus: Customer coordinates as entered by the user.
        res_pos: Restaurant grid-cell centre ``(x, y)``.
        cus_pos: Customer grid-cell centre ``(x, y)``.
        status: One of "created", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: ID of the assigned rider, or None.
        start_time: Simulated tick when the order was created.
        completed_time: Simulated tick of delivery, or None.
        distance: Street route length from restaurant to customer.
        time_taken: Ticks from creation to delivery, or None.
        efficiency: Distance per tick (units/tick), or None.
    """

    _id_counter = 0

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and convert its coordinates to grid centres.

        Args:
            res_pos: Restaurant coordinates ``(x, y)`` in range 0-800.
            cus_pos: Customer coordinates ``(x, y)`` in range 0-800.

        Raises:
            TypeError: If a coordinate is not an integer.
            ValueError: If a coordinate is outside 0-800.
        """
        raw_res = _split_position(res_pos, "restaurant")
        raw_cus = _split_position(cus_pos, "customer")

        Order._id_counter += 1
        self.id: int = Order._id_counter
        self.raw_res: Tuple[int, int] = raw_res
        self.raw_cus: Tuple[int, int] = raw_cus
        self.res_pos: Tuple[int, int] = to_grid_center(*raw_res)
        self.cus_pos: Tuple[int, int] = to_grid_center(*raw_cus)
        self.status: str = STATUS_CREATED
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("time", 0) or 0)
        self.completed_time: Optional[int] = None
        self.distance: int = path_length(
            PathPlanner().plan(self.res_pos, self.cus_pos))
        self.time_taken: Optional[int] = None
        self.efficiency: Optional[float] = None

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_completed(self, time: int) -> None:
        """Mark the order as delivered and compute efficiency data.

        Args:
            time: Simulated tick at which delivery finished.
        """
        self.status = STATUS_COMPLETED
        self.completed_time = time
        self.time_taken = max(time - self.start_time, 0)
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "raw_res": list(self.raw_res),
            "raw_cus": list(self.raw_cus),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completed_time": self.completed_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
